<script lang="ts">
	import { clientApi } from '$lib/client';

	interface HealthRow {
		company_id: number;
		name: string;
		slug: string;
		category: string;
		verified: boolean;
		careers_url: string | null;
		last_scrape_status: string | null;
		last_scrape_at: string | null;
		last_jobs_found: number | null;
		consecutive_failures: number;
		active_rows: number;
		described_share: number;
		role_share: number;
		board_count: number;
		grade: string;
	}

	interface HealthSummary {
		failing: number;
		furniture: number;
		thin: number;
		idle: number;
		healthy: number;
	}

	interface HealthResponse {
		items: HealthRow[];
		total: number;
		page: number;
		per_page: number;
		pages: number;
		summary: HealthSummary;
	}

	const GRADES = ['failing', 'furniture', 'thin', 'idle', 'healthy'] as const;
	type Grade = (typeof GRADES)[number];

	const GRADE_LABELS: Record<Grade, string> = {
		failing: 'Failing',
		furniture: 'Furniture',
		thin: 'Thin',
		idle: 'Idle',
		healthy: 'Healthy'
	};

	let rows = $state<HealthRow[]>([]);
	let summary = $state<HealthSummary>({ failing: 0, furniture: 0, thin: 0, idle: 0, healthy: 0 });
	let loading = $state(true);
	let message = $state('');
	let search = $state('');
	let gradeFilter = $state<Grade | null>(null);
	let page = $state(1);
	let sort = $state<'grade' | 'board' | 'active' | 'name'>('grade');
	let direction = $state<'asc' | 'desc'>('desc');
	let pageData = $state({ total: 0, page: 1, pages: 0 });

	const DEFAULT_DIRECTION: Record<string, 'asc' | 'desc'> = {
		grade: 'desc',
		board: 'desc',
		active: 'desc',
		name: 'asc'
	};

	function query(overrides: Record<string, string> = {}) {
		const params = new URLSearchParams({
			per_page: '50',
			page: String(page),
			sort,
			direction,
			...overrides
		});
		if (search.trim()) params.set('q', search.trim());
		if (gradeFilter) params.set('grade', gradeFilter);
		return params;
	}

	async function load() {
		loading = true;
		try {
			const table = await clientApi<HealthResponse>(
				`/api/admin/companies/health?${query().toString()}`
			);
			rows = table.items;
			pageData = { total: table.total, page: table.page, pages: table.pages };

			const summaryParams = query({ page: '1', per_page: '1' });
			summaryParams.delete('grade');
			const forSummary = await clientApi<HealthResponse>(
				`/api/admin/companies/health?${summaryParams.toString()}`
			);
			summary = forSummary.summary;
		} catch (err) {
			message = err instanceof Error ? err.message : 'Failed to load';
		} finally {
			loading = false;
		}
	}

	let searchTimer: ReturnType<typeof setTimeout> | undefined;
	function onSearch() {
		page = 1;
		clearTimeout(searchTimer);
		searchTimer = setTimeout(load, 300);
	}

	function toggleGrade(grade: Grade) {
		gradeFilter = gradeFilter === grade ? null : grade;
		page = 1;
		load();
	}

	function sortBy(column: 'grade' | 'board' | 'active' | 'name') {
		if (sort === column) {
			direction = direction === 'asc' ? 'desc' : 'asc';
		} else {
			sort = column;
			direction = DEFAULT_DIRECTION[column];
		}
		page = 1;
		load();
	}

	function sortMark(column: string) {
		if (sort !== column) return '';
		return direction === 'asc' ? ' ↑' : ' ↓';
	}

	function ariaSort(column: string) {
		if (sort !== column) return 'none';
		return direction === 'asc' ? 'ascending' : 'descending';
	}

	function prevPage() {
		if (page <= 1) return;
		page -= 1;
		load();
	}

	function nextPage() {
		if (page >= pageData.pages) return;
		page += 1;
		load();
	}

	function pct(share: number): string {
		return `${Math.round(share * 100)}%`;
	}

	$effect(() => {
		load();
		return () => clearTimeout(searchTimer);
	});
</script>

<section class="mt-10">
	<h1 class="text-title font-semibold">Company health</h1>
	<p class="mt-2 max-w-prose text-meta leading-relaxed text-muted">
		Verified only means a human confirmed the careers URL, not that the scrape produces real
		jobs. This view derives each company's grade at query time from what its active rows
		actually look like — nothing here is stored.
	</p>

	<div class="mt-6 flex flex-wrap items-center gap-1.5" role="group" aria-label="Filter by grade">
		{#each GRADES as grade (grade)}
			<button
				type="button"
				class="btn btn-quiet {gradeFilter === grade ? 'is-on' : ''}"
				aria-pressed={gradeFilter === grade}
				onclick={() => toggleGrade(grade)}
			>
				{GRADE_LABELS[grade]}
				<span class="coord">{summary[grade]}</span>
			</button>
		{/each}
	</div>

	<p class="mt-4 max-w-prose text-meta leading-relaxed text-muted">
		A 0% described share is a strong suspicion of furniture — nav chrome, blog posts, location
		listings — not proof: some ATS integrations legitimately return titles with no description
		text at all. Read the titles before treating a grade as a verdict.
	</p>

	<div class="mt-6 flex flex-wrap items-center gap-3">
		<label class="sr-only" for="health-search">Search companies</label>
		<input
			id="health-search"
			bind:value={search}
			oninput={onSearch}
			placeholder="Search by name…"
			class="field h-10 w-full max-w-xs sm:w-72"
		/>
	</div>

	{#if message}<p class="coord mt-4" role="status">{message}</p>{/if}

	<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
	<div
		class="mt-6 overflow-x-auto"
		tabindex="0"
		role="region"
		aria-label="Company health, scrollable table"
	>
		<table class="w-full min-w-[72rem] text-left text-meta">
			<caption class="sr-only">
				Companies with their derived health grade, board count, active row count, described
				and role share, last scrape status and consecutive failures
			</caption>
			<thead>
				<tr class="axis-label border-b border-muted">
					<th scope="col" class="px-4 py-2.5 font-medium" aria-sort={ariaSort('name')}>
						<button type="button" class="hover:underline" onclick={() => sortBy('name')}>
							Company{sortMark('name')}
						</button>
					</th>
					<th scope="col" class="px-4 py-2.5 font-medium" aria-sort={ariaSort('grade')}>
						<button type="button" class="hover:underline" onclick={() => sortBy('grade')}>
							Grade{sortMark('grade')}
						</button>
					</th>
					<th scope="col" class="px-4 py-2.5 font-medium" aria-sort={ariaSort('board')}>
						<button type="button" class="hover:underline" onclick={() => sortBy('board')}>
							On board{sortMark('board')}
						</button>
					</th>
					<th scope="col" class="px-4 py-2.5 font-medium" aria-sort={ariaSort('active')}>
						<button type="button" class="hover:underline" onclick={() => sortBy('active')}>
							Active{sortMark('active')}
						</button>
					</th>
					<th scope="col" class="px-4 py-2.5 font-medium">Described</th>
					<th scope="col" class="px-4 py-2.5 font-medium">Role share</th>
					<th scope="col" class="px-4 py-2.5 font-medium">Last scrape</th>
					<th scope="col" class="px-4 py-2.5 font-medium">Failures</th>
				</tr>
			</thead>
			<tbody>
				{#each rows as row (row.company_id)}
					<tr class="border-b border-rule align-top last:border-0">
						<th scope="row" class="px-4 py-3 font-semibold">
							<a href="/companies/{row.slug}" target="_blank" rel="noopener noreferrer" class="link">
								{row.name}
							</a>
							<span class="coord block text-muted">{row.category}</span>
						</th>
						<td class="px-4 py-3 {row.grade === 'healthy' ? 'text-muted' : 'font-bold'}">
							{GRADE_LABELS[row.grade as Grade] ?? row.grade}
						</td>
						<td class="coord px-4 py-3">{row.board_count}</td>
						<td class="coord px-4 py-3">{row.active_rows}</td>
						<td class="coord px-4 py-3">{pct(row.described_share)}</td>
						<td class="coord px-4 py-3">{pct(row.role_share)}</td>
						<td class="coord px-4 py-3">
							{row.last_scrape_status ?? 'never'}
							{#if row.last_scrape_at}
								<span class="block text-muted">{new Date(row.last_scrape_at).toLocaleDateString()}</span>
							{/if}
						</td>
						<td class="coord px-4 py-3">
							{row.consecutive_failures}
						</td>
					</tr>
				{:else}
					<tr>
						<td colspan="8" class="px-4 py-6 text-center text-meta text-muted">
							{loading ? 'Loading…' : 'No companies match.'}
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>

	<div class="mt-6 flex items-center justify-center gap-3">
		<button type="button" class="btn btn-quiet" disabled={page <= 1} onclick={prevPage}><svg width="12" height="12" viewBox="0 0 16 16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M13 8H3M7 4L3 8l4 4"/></svg>Prev</button>
		<span class="coord text-muted">
			Page {pageData.page} of {pageData.pages} · {pageData.total} companies
		</span>
		<button type="button" class="btn btn-quiet" disabled={page >= pageData.pages} onclick={nextPage}>Next<svg width="12" height="12" viewBox="0 0 16 16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M3 8h10M9 4l4 4-4 4"/></svg></button>
	</div>
</section>
