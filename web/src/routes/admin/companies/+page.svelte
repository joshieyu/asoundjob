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
		<table class="w-full min-w-[72rem] text-left text-sm">
			<thead>
				<tr class="border-b border-seam font-mono text-[10px] tracking-[0.12em] text-ink-soft uppercase">
					<th scope="col" class="px-4 py-2.5" aria-sort={ariaSort('name')}>
						<button type="button" class="uppercase tracking-[0.12em] hover:underline" onclick={() => sortBy('name')}>
							Company{sortMark('name')}
						</button>
					</th>
					<th scope="col" class="px-4 py-2.5">Category</th>
					<th scope="col" class="px-4 py-2.5" aria-sort={ariaSort('jobs')}>
						<button type="button" class="uppercase tracking-[0.12em] hover:underline" onclick={() => sortBy('jobs')} title="Rows the scraper is holding, junk included">
							Scraped{sortMark('jobs')}
						</button>
					</th>
					<th scope="col" class="px-4 py-2.5" aria-sort={ariaSort('board')}>
						<button type="button" class="uppercase tracking-[0.12em] hover:underline" onclick={() => sortBy('board')} title="Rows a reader actually sees on the public board">
							On board{sortMark('board')}
						</button>
					</th>
					<th scope="col" class="px-4 py-2.5">Careers URL</th>
					<th scope="col" class="px-4 py-2.5" aria-sort={ariaSort('verified')}>
						<button type="button" class="uppercase tracking-[0.12em] hover:underline" onclick={() => sortBy('verified')}>
							Verified{sortMark('verified')}
						</button>
					</th>
					<th scope="col" class="px-4 py-2.5">Actions</th>
				</tr>
			</thead>
			<tbody>
				{#each companies as row (row.id)}
					<tr class="border-b border-seam/60 align-top last:border-0">
						<td class="px-4 py-3 font-semibold">
							{#if editingId === row.id && editingKind === 'name'}
								<span class="flex items-center gap-1.5">
									<input bind:value={nameValue} class="well h-8 w-44 px-2 text-xs font-normal" />
									<button type="button" class="btn-latch !py-1" onclick={() => saveName(row)}>Save</button>
									<button type="button" class="btn-latch !py-1" onclick={cancelEdit}>Cancel</button>
								</span>
							{:else}
								<span class="flex items-center gap-1.5">
									{row.name}
									<button type="button" class="btn-latch !py-1 !normal-case" onclick={() => startEditName(row)}>Edit</button>
								</span>
							{/if}
						</td>
						<td class="px-4 py-3 text-xs text-ink-soft">{row.category}</td>
						<td class="readout px-4 py-3">{row.active_jobs_count}</td>
						<td class="readout px-4 py-3 {row.active_jobs_count > 0 && row.board_jobs_count === 0 ? 'text-ink-soft' : ''}">
							{row.board_jobs_count}
						</td>
						<td class="px-4 py-3">
							{#if editingId === row.id && editingKind === 'url'}
								<span class="flex flex-col gap-1.5">
									<textarea
										bind:value={editValue}
										rows="3"
										placeholder="https://example.com/careers"
										class="well w-72 px-2 py-1.5 font-mono text-xs"
									></textarea>
									<span class="flex gap-1.5">
										<button type="button" class="btn-latch !py-1" onclick={() => saveUrls(row)}>Save</button>
										<button type="button" class="btn-latch !py-1" onclick={cancelEdit}>Cancel</button>
									</span>
								</span>
							{:else if row.careers_url}
								<span class="flex flex-col gap-0.5">
									<span class="flex items-center gap-1.5">
										<a
											href={row.careers_url}
											target="_blank"
											rel="noopener noreferrer"
											class="max-w-[16rem] truncate font-mono text-xs text-fader-deep hover:underline"
										>
											{row.careers_url}
										</a>
										{#if row.extra_careers_urls?.length}
											<span class="font-mono text-[10px] text-ink-soft" title="{row.extra_careers_urls.length} additional careers URL(s)">
												+{row.extra_careers_urls.length}
											</span>
										{/if}
										<button type="button" class="btn-latch !py-1" onclick={() => startEditUrls(row)}>Edit</button>
									</span>
									{#if row.extra_careers_urls?.length}
										<span class="flex flex-col gap-0.5">
											{#each row.extra_careers_urls as extra}
												<a
													href={extra}
													target="_blank"
													rel="noopener noreferrer"
													class="max-w-[16rem] truncate font-mono text-[10px] text-ink-soft hover:underline"
												>
													{extra}
												</a>
											{/each}
										</span>
									{/if}
								</span>
							{:else}
								<button type="button" class="btn-latch !py-1" onclick={() => startEditUrls(row)}>Add URL</button>
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
						<td class="px-4 py-3">
							{#if deletingId === row.id}
								<span class="flex flex-col gap-1.5">
									<span class="max-w-[14rem] font-mono text-[10px] text-ink-soft">
										Really delete {row.name}? Removes the company, {row.active_jobs_count} scraped job{row.active_jobs_count === 1 ? '' : 's'}, and its scrape history.
									</span>
									<span class="flex gap-1.5">
										<button type="button" class="btn-latch !py-1" onclick={() => deleteCompany(row)}>Yes</button>
										<button type="button" class="btn-latch !py-1" onclick={cancelDelete}>No</button>
									</span>
								</span>
							{:else}
								<button type="button" class="btn-latch !py-1" onclick={() => startDelete(row)}>Delete</button>
							{/if}
						</td>
					</tr>
				{:else}
					<tr>
						<td colspan="7" class="px-4 py-6 text-center font-mono text-sm text-ink-soft">
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
		Edits flip a row to source=manual, so the nightly reload of
		data/audio_companies_final.json skips it — renames and other edits persist. That seed
		file itself still holds the old values, and a deleted company isn't protected at all:
		the next cycle re-inserts it straight from the seed. Run
		python -m scraper.export_seed_edits to produce a candidate seed file and diff report
		for the owner to review and apply by hand.
	</p>
</section>
