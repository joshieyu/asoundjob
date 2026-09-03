<script lang="ts">
	import { clientApi } from '$lib/client';

	interface CompanyRow {
		id: number;
		name: string;
		slug: string;
		category: string;
		careers_url: string | null;
		verified: boolean;
		source: string;
		active_jobs_count: number;
	}

	let companies = $state<CompanyRow[]>([]);
	let search = $state('');
	let loading = $state(true);
	let editingUrl = $state(0);
	let editValue = $state('');
	let message = $state('');
	let page = $state(1);
	let sort = $state<'name' | 'jobs' | 'verified'>('name');
	let direction = $state<'asc' | 'desc'>('asc');
	let pageData = $state({ total: 0, page: 1, pages: 0 });

	async function load() {
		loading = true;
		try {
			const query = new URLSearchParams({
				per_page: '50',
				page: String(page),
				sort,
				direction
			});
			if (search.trim()) query.set('search', search.trim());
			const result = await clientApi<{ items: CompanyRow[]; total: number; page: number; pages: number }>(
				`/api/admin/companies?${query.toString()}`
			);
			companies = result.items;
			pageData = { total: result.total, page: result.page, pages: result.pages };
		} catch (err) {
			message = err instanceof Error ? err.message : 'Failed to load';
		} finally {
			loading = false;
		}
	}

	const DEFAULT_DIRECTION: Record<string, 'asc' | 'desc'> = {
		name: 'asc',
		jobs: 'desc',
		verified: 'desc'
	};

	function sortBy(column: 'name' | 'jobs' | 'verified') {
		if (sort === column) {
			direction = direction === 'asc' ? 'desc' : 'asc';
		} else {
			sort = column;
			direction = DEFAULT_DIRECTION[column];
		}
		page = 1;
		load();
	}

	function sortMark(column: 'name' | 'jobs' | 'verified') {
		if (sort !== column) return '';
		return direction === 'asc' ? ' ↑' : ' ↓';
	}

	function ariaSort(column: 'name' | 'jobs' | 'verified') {
		if (sort !== column) return 'none';
		return direction === 'asc' ? 'ascending' : 'descending';
	}

	let searchTimer: ReturnType<typeof setTimeout> | undefined;
	function onSearch() {
		page = 1;
		clearTimeout(searchTimer);
		searchTimer = setTimeout(load, 300);
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

	$effect(() => {
		load();
		return () => clearTimeout(searchTimer);
	});

	async function toggleVerified(row: CompanyRow) {
		message = '';
		try {
			await clientApi(`/api/admin/companies/${row.id}`, {
				method: 'PUT',
				body: { verified: !row.verified }
			});
			row.verified = !row.verified;
			row.source = row.verified ? 'manual' : row.source;
			message = `${row.name} marked ${row.verified ? 'verified' : 'unverified'}.`;
		} catch (err) {
			message = err instanceof Error ? err.message : 'Update failed';
		}
	}

	function startEdit(row: CompanyRow) {
		editingUrl = row.id;
		editValue = row.careers_url ?? '';
	}

	function cancelEdit() {
		editingUrl = 0;
	}

	async function saveUrl(id: number, name: string) {
		message = '';
		try {
			await clientApi(`/api/admin/companies/${id}`, {
				method: 'PUT',
				body: { careers_url: editValue }
			});
			const row = companies.find((c) => c.id === id);
			if (row) row.careers_url = editValue;
			editingUrl = 0;
			message = `Updated ${name}.`;
		} catch (err) {
			message = err instanceof Error ? err.message : 'Update failed';
		}
	}
</script>

<section class="mt-6">
	<h1 class="legend">COMPANY MANAGEMENT</h1>

	<div class="mt-4 flex flex-wrap items-center gap-3">
		<label class="sr-only" for="company-search">Search companies</label>
		<input
			id="company-search"
			bind:value={search}
			oninput={onSearch}
			placeholder="Search by name…"
			class="well h-10 w-full max-w-xs px-3 text-sm sm:w-72"
		/>
	</div>

	{#if message}<p class="mt-3 font-mono text-xs tracking-wide" role="status">{message}</p>{/if}

	<div class="panel mt-4 overflow-x-auto">
		<table class="w-full min-w-[48rem] text-left text-sm">
			<thead>
				<tr class="border-b border-seam font-mono text-[10px] tracking-[0.12em] text-ink-soft uppercase">
					<th scope="col" class="px-4 py-2.5" aria-sort={ariaSort('name')}>
						<button type="button" class="uppercase tracking-[0.12em] hover:underline" onclick={() => sortBy('name')}>
							Company{sortMark('name')}
						</button>
					</th>
					<th scope="col" class="px-4 py-2.5">Category</th>
					<th scope="col" class="px-4 py-2.5" aria-sort={ariaSort('jobs')}>
						<button type="button" class="uppercase tracking-[0.12em] hover:underline" onclick={() => sortBy('jobs')}>
							Open jobs{sortMark('jobs')}
						</button>
					</th>
					<th scope="col" class="px-4 py-2.5">Careers URL</th>
					<th scope="col" class="px-4 py-2.5" aria-sort={ariaSort('verified')}>
						<button type="button" class="uppercase tracking-[0.12em] hover:underline" onclick={() => sortBy('verified')}>
							Verified{sortMark('verified')}
						</button>
					</th>
				</tr>
			</thead>
			<tbody>
				{#each companies as row (row.id)}
					<tr class="border-b border-seam/60 align-top last:border-0">
						<td class="px-4 py-3 font-semibold">{row.name}</td>
						<td class="px-4 py-3 text-xs text-ink-soft">{row.category}</td>
						<td class="readout px-4 py-3">{row.active_jobs_count}</td>
						<td class="px-4 py-3">
							{#if editingUrl === row.id}
								<span class="flex gap-1.5">
									<input bind:value={editValue} class="well h-8 w-64 px-2 font-mono text-xs" />
									<button type="button" class="btn-latch !py-1" onclick={() => saveUrl(row.id, row.name)}>Save</button>
									<button type="button" class="btn-latch !py-1" onclick={cancelEdit}>Cancel</button>
								</span>
							{:else if row.careers_url}
								<span class="flex items-center gap-1.5">
									<a
										href={row.careers_url}
										target="_blank"
										rel="noopener noreferrer"
										class="max-w-[16rem] truncate font-mono text-xs text-fader-deep hover:underline"
									>
										{row.careers_url}
									</a>
									<button type="button" class="btn-latch !py-1" onclick={() => startEdit(row)}>Edit</button>
								</span>
							{:else}
								<button type="button" class="btn-latch !py-1" onclick={() => startEdit(row)}>Add URL</button>
							{/if}
						</td>
						<td class="px-4 py-3">
							<button type="button" class="btn-latch !py-1 {row.verified ? 'is-on' : ''}" onclick={() => toggleVerified(row)}>
								{row.verified ? 'Yes' : 'No'}
							</button>
							{#if row.source === 'manual'}
								<span class="ml-1.5 font-mono text-[10px] text-fader-deep" title="Manually verified">M</span>
							{/if}
						</td>
					</tr>
				{:else}
					<tr>
						<td colspan="5" class="px-4 py-6 text-center font-mono text-sm text-ink-soft">
							{loading ? 'Loading…' : 'No companies match.'}
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>

	<div class="mt-3 flex items-center justify-center gap-3">
		<button type="button" class="btn-latch" disabled={page <= 1} onclick={prevPage}>← Prev</button>
		<span class="font-mono text-xs text-ink-soft">
			Page {pageData.page} of {pageData.pages} · {pageData.total} companies
		</span>
		<button type="button" class="btn-latch" disabled={page >= pageData.pages} onclick={nextPage}>Next →</button>
	</div>

	<p class="mt-2 font-mono text-[11px] tracking-wide text-ink-soft">
		Edits mark the company source=manual — the nightly sync will never overwrite it.
	</p>
</section>
