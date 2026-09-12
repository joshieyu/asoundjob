<script lang="ts">
	import { clientApi } from '$lib/client';

	interface CompanyRow {
		id: number;
		name: string;
		slug: string;
		category: string;
		careers_url: string | null;
		extra_careers_urls: string[] | null;
		open_application: boolean;
		verified: boolean;
		source: string;
		active_jobs_count: number;
		board_jobs_count: number;
	}

	let companies = $state<CompanyRow[]>([]);
	let search = $state('');
	let loading = $state(true);
	let editingId = $state(0);
	let editingKind = $state<'name' | 'url' | null>(null);
	let editValue = $state('');
	let nameValue = $state('');
	let deletingId = $state(0);
	let message = $state('');
	let page = $state(1);
	let sort = $state<'name' | 'jobs' | 'board' | 'verified'>('name');
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
		board: 'desc',
		verified: 'desc'
	};

	function sortBy(column: 'name' | 'jobs' | 'board' | 'verified') {
		if (sort === column) {
			direction = direction === 'asc' ? 'desc' : 'asc';
		} else {
			sort = column;
			direction = DEFAULT_DIRECTION[column];
		}
		page = 1;
		load();
	}

	function sortMark(column: 'name' | 'jobs' | 'board' | 'verified') {
		if (sort !== column) return '';
		return direction === 'asc' ? ' ↑' : ' ↓';
	}

	function ariaSort(column: 'name' | 'jobs' | 'board' | 'verified') {
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

	function cancelEdit() {
		editingId = 0;
		editingKind = null;
	}

	function cancelDelete() {
		deletingId = 0;
	}

	function startEditUrls(row: CompanyRow) {
		deletingId = 0;
		editingId = row.id;
		editingKind = 'url';
		const lines = [row.careers_url, ...(row.extra_careers_urls ?? [])].filter(
			(url): url is string => !!url
		);
		editValue = lines.join('\n');
	}

	function startEditName(row: CompanyRow) {
		deletingId = 0;
		editingId = row.id;
		editingKind = 'name';
		nameValue = row.name;
	}

	function startDelete(row: CompanyRow) {
		cancelEdit();
		deletingId = row.id;
	}

	async function saveUrls(row: CompanyRow) {
		message = '';
		const lines = editValue
			.split('\n')
			.map((line) => line.trim())
			.filter((line) => line.length > 0);
		if (lines.length > 6) {
			message = 'At most 6 URLs total: 1 primary careers URL plus up to 5 extras.';
			return;
		}
		if (lines.some((line) => !line.startsWith('http://') && !line.startsWith('https://'))) {
			message = 'Every URL must start with http:// or https://.';
			return;
		}
		const [primary, ...extras] = lines;
		try {
			await clientApi(`/api/admin/companies/${row.id}`, {
				method: 'PUT',
				body: { careers_url: primary ?? '', extra_careers_urls: extras }
			});
			row.careers_url = primary ?? '';
			row.extra_careers_urls = extras;
			cancelEdit();
			message = `Updated ${row.name}.`;
		} catch (err) {
			message = err instanceof Error ? err.message : 'Update failed';
		}
	}

	async function saveName(row: CompanyRow) {
		message = '';
		const trimmed = nameValue.trim();
		try {
			await clientApi(`/api/admin/companies/${row.id}`, {
				method: 'PUT',
				body: { name: trimmed }
			});
			row.name = trimmed;
			cancelEdit();
			message = `Updated ${row.name}.`;
		} catch (err) {
			message = err instanceof Error ? err.message : 'Rename failed';
		}
	}

	async function deleteCompany(row: CompanyRow) {
		message = '';
		try {
			const result = await clientApi<{
				deleted: { company: string; jobs: number; scrape_logs: number; submissions_detached: number };
			}>(`/api/admin/companies/${row.id}`, { method: 'DELETE' });
			companies = companies.filter((c) => c.id !== row.id);
			pageData = { ...pageData, total: pageData.total - 1 };
			deletingId = 0;
			const d = result.deleted;
			message = `Deleted ${d.company} — removed ${d.jobs} scraped job${d.jobs === 1 ? '' : 's'} and ${d.scrape_logs} scrape log${d.scrape_logs === 1 ? '' : 's'}${d.submissions_detached ? `, detached ${d.submissions_detached} submission${d.submissions_detached === 1 ? '' : 's'}` : ''}.`;
		} catch (err) {
			message = err instanceof Error ? err.message : 'Delete failed';
			deletingId = 0;
		}
	}
</script>

<section class="mt-10">
	<h1 class="text-title font-semibold">Company management</h1>

	<div class="mt-6 flex flex-wrap items-center gap-3">
		<label class="sr-only" for="company-search">Search companies</label>
		<input
			id="company-search"
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
		aria-label="Companies, scrollable table"
	>
		<table class="w-full min-w-[72rem] text-left text-meta">
			<caption class="sr-only">
				Companies with their category, scraped job count, count on the public board, careers URLs, verified state and row actions
			</caption>
			<thead>
				<tr class="axis-label border-b border-muted">
					<th scope="col" class="px-4 py-2.5 font-medium" aria-sort={ariaSort('name')}>
						<button type="button" class="hover:underline" onclick={() => sortBy('name')}>
							Company{sortMark('name')}
						</button>
					</th>
					<th scope="col" class="px-4 py-2.5 font-medium">Category</th>
					<th scope="col" class="px-4 py-2.5 font-medium" aria-sort={ariaSort('jobs')}>
						<button type="button" class="hover:underline" onclick={() => sortBy('jobs')} title="Rows the scraper is holding, junk included">
							Scraped{sortMark('jobs')}
						</button>
					</th>
					<th scope="col" class="px-4 py-2.5 font-medium" aria-sort={ariaSort('board')}>
						<button type="button" class="hover:underline" onclick={() => sortBy('board')} title="Rows a reader actually sees on the public board">
							On board{sortMark('board')}
						</button>
					</th>
					<th scope="col" class="px-4 py-2.5 font-medium">Careers URL</th>
					<th scope="col" class="px-4 py-2.5 font-medium" aria-sort={ariaSort('verified')}>
						<button type="button" class="hover:underline" onclick={() => sortBy('verified')}>
							Verified{sortMark('verified')}
						</button>
					</th>
					<th scope="col" class="px-4 py-2.5 font-medium">Actions</th>
				</tr>
			</thead>
			<tbody>
				{#each companies as row (row.id)}
					<tr class="border-b border-rule align-top last:border-0">
						<th scope="row" class="px-4 py-3 font-semibold">
							{#if editingId === row.id && editingKind === 'name'}
								<span class="flex items-center gap-1.5">
									<input bind:value={nameValue} class="field h-8 w-44 font-normal" />
									<button type="button" class="btn btn-quiet px-2 py-1" onclick={() => saveName(row)}>Save</button>
									<button type="button" class="btn btn-quiet px-2 py-1" onclick={cancelEdit}>Cancel</button>
								</span>
							{:else}
								<span class="flex items-center gap-3">
									<span class="min-w-0">{row.name}</span>
									<button type="button" class="btn btn-quiet ml-auto shrink-0 px-2 py-1" onclick={() => startEditName(row)}>Edit</button>
								</span>
							{/if}
						</th>
						<td class="coord px-4 py-3 text-muted">{row.category}</td>
						<td class="coord px-4 py-3">{row.active_jobs_count}</td>
						<td class="coord px-4 py-3">
							{row.board_jobs_count}
							{#if row.active_jobs_count > 0 && row.board_jobs_count === 0}
								<span class="block text-muted" title="Every scraped job for this company is filtered off the public board">
									all filtered off
								</span>
							{/if}
						</td>
						<td class="px-4 py-3">
							{#if editingId === row.id && editingKind === 'url'}
								<span class="flex flex-col gap-1.5">
									<textarea
										bind:value={editValue}
										rows="3"
										placeholder="https://example.com/careers"
										class="field coord w-72"
									></textarea>
									<span class="flex gap-1.5">
										<button type="button" class="btn btn-quiet px-2 py-1" onclick={() => saveUrls(row)}>Save</button>
										<button type="button" class="btn btn-quiet px-2 py-1" onclick={cancelEdit}>Cancel</button>
									</span>
								</span>
							{:else if row.careers_url}
								<span class="flex flex-col gap-0.5">
									<span class="flex items-center gap-3">
										<a
											href={row.careers_url}
											target="_blank"
											rel="noopener noreferrer"
											class="link coord max-w-[16rem] truncate"
										>
											{row.careers_url}
										</a>
										<span class="ml-auto flex shrink-0 items-center gap-1.5">
											{#if row.extra_careers_urls?.length}
												<span class="coord text-muted" title="{row.extra_careers_urls.length} additional careers URL(s)">
													+{row.extra_careers_urls.length}
												</span>
											{/if}
											<button type="button" class="btn btn-quiet px-2 py-1" onclick={() => startEditUrls(row)}>Edit</button>
										</span>
									</span>
									{#if row.extra_careers_urls?.length}
										<span class="flex flex-col gap-0.5">
											{#each row.extra_careers_urls as extra}
												<a
													href={extra}
													target="_blank"
													rel="noopener noreferrer"
													class="coord max-w-[16rem] truncate text-muted underline"
												>
													{extra}
												</a>
											{/each}
										</span>
									{/if}
								</span>
							{:else}
								<span class="flex">
									<button type="button" class="btn btn-quiet ml-auto shrink-0 px-2 py-1" onclick={() => startEditUrls(row)}>Add URL</button>
								</span>
							{/if}
						</td>
						<td class="px-4 py-3">
							<span class="flex items-center gap-1.5">
								<button
									type="button"
									class="btn btn-quiet px-2 py-1 {row.verified ? 'is-on' : ''}"
									onclick={() => toggleVerified(row)}
								>
									{row.verified ? 'Yes' : 'No'}
								</button>
								{#if row.source === 'manual'}
									<span class="coord text-ink" title="Manually verified">M<span class="sr-only"> — manually verified</span></span>
								{/if}
							</span>
						</td>
						<td class="px-4 py-3">
							{#if deletingId === row.id}
								<span class="flex flex-col gap-1.5">
									<span class="coord max-w-[14rem] text-muted">
										Really delete {row.name}? Removes the company, {row.active_jobs_count} scraped job{row.active_jobs_count === 1 ? '' : 's'}, and its scrape history.
									</span>
									<span class="flex gap-1.5">
										<button type="button" class="btn btn-quiet px-2 py-1" onclick={() => deleteCompany(row)}>Yes</button>
										<button type="button" class="btn btn-quiet px-2 py-1" onclick={cancelDelete}>No</button>
									</span>
								</span>
							{:else}
								<button type="button" class="btn btn-quiet px-2 py-1" onclick={() => startDelete(row)}>Delete</button>
							{/if}
						</td>
					</tr>
				{:else}
					<tr>
						<td colspan="7" class="px-4 py-6 text-center text-meta text-muted">
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

	<p class="mt-10 max-w-prose text-meta leading-relaxed text-muted">
		Edits flip a row to source=manual, so the nightly reload of
		data/audio_companies_final.json skips it — renames and other edits persist. That seed
		file itself still holds the old values, and a deleted company isn't protected at all:
		the next cycle re-inserts it straight from the seed. Run
		python -m scraper.export_seed_edits to produce a candidate seed file and diff report
		for the owner to review and apply by hand.
	</p>
</section>
