<script lang="ts">
	import { clientApi } from '$lib/client';

	interface JobRow {
		id: number;
		title: string;
		company_name: string | null;
		url: string;
		location: string | null;
		source: string;
		is_active: boolean;
		is_audio_related: boolean;
		relevance_score: number;
		is_audio_related_override: boolean | null;
		on_board: boolean;
	}

	type Show = 'all' | 'hidden' | 'overridden';

	const SHOW_LABELS: [Show, string][] = [
		['all', 'All jobs'],
		['hidden', 'Hidden as not audio'],
		['overridden', 'Set by hand']
	];

	let rows = $state<JobRow[]>([]);
	let search = $state('');
	let show = $state<Show>('all');
	let page = $state(1);
	let pageData = $state({ total: 0, page: 1, pages: 0 });
	let loading = $state(true);
	let message = $state('');
	let busyId = $state<number | null>(null);

	async function load() {
		loading = true;
		try {
			const query = new URLSearchParams({ per_page: '50', page: String(page), show });
			if (search.trim()) query.set('search', search.trim());
			const result = await clientApi<{ items: JobRow[]; total: number; page: number; pages: number }>(
				`/api/admin/jobs?${query}`
			);
			rows = result.items;
			pageData = { total: result.total, page: result.page, pages: result.pages };
		} catch (err) {
			message = err instanceof Error ? err.message : 'Failed to load jobs';
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

	function setShow(next: Show) {
		show = next;
		page = 1;
		load();
	}

	function go(delta: number) {
		page += delta;
		load();
	}

	$effect(() => {
		load();
		return () => clearTimeout(searchTimer);
	});

	function decision(row: JobRow): string {
		if (row.is_audio_related_override === true) return 'Audio, set by hand';
		if (row.is_audio_related_override === false) return 'Not audio, set by hand';
		return row.is_audio_related ? 'Audio, by score' : 'Not audio, by score';
	}

	async function setAudio(row: JobRow, value: boolean | null) {
		busyId = row.id;
		message = '';
		try {
			const updated = await clientApi<JobRow>(`/api/admin/jobs/${row.id}/audio`, {
				method: 'PUT',
				body: { is_audio_related: value }
			});
			rows = rows.map((r) => (r.id === row.id ? updated : r));
			message =
				value === null
					? `“${row.title}” is back to its score (${updated.on_board ? 'on the board' : 'hidden'}).`
					: value
						? `“${row.title}” is on the board and stays there across scrapes.`
						: `“${row.title}” is hidden as not audio and stays hidden across scrapes.`;
		} catch (err) {
			message = err instanceof Error ? err.message : 'Update failed';
		} finally {
			busyId = null;
		}
	}
</script>

<section class="mt-10">
	<h1 class="text-title font-semibold">Jobs</h1>
	<p class="mt-2 max-w-prose text-meta leading-relaxed text-muted">
		Find any scraped or community job, including ones the relevance score hides, and decide by
		hand whether it belongs on the board. A hand decision survives every future scrape and
		re-score until you return the job to its score.
	</p>

	<div class="mt-6 flex flex-wrap items-center gap-3">
		<label class="sr-only" for="job-search">Search jobs</label>
		<input
			id="job-search"
			bind:value={search}
			oninput={onSearch}
			placeholder="Title, company, or paste a job URL…"
			class="field h-10 w-full max-w-md sm:w-96"
		/>
		<div class="flex flex-wrap gap-1.5" role="group" aria-label="Which jobs to show">
			{#each SHOW_LABELS as [value, label] (value)}
				<button
					type="button"
					class="btn btn-quiet"
					class:is-on={show === value}
					aria-pressed={show === value}
					onclick={() => setShow(value)}
				>
					{label}
				</button>
			{/each}
		</div>
	</div>

	{#if message}<p class="mt-4 text-meta font-semibold" role="status">{message}</p>{/if}

	{#if loading && rows.length === 0}
		<p class="mt-6 text-meta text-muted">Loading jobs…</p>
	{:else if rows.length === 0}
		<p class="mt-6 text-meta text-muted">No jobs match.</p>
	{:else}
		<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
		<div class="mt-6 overflow-x-auto" tabindex="0" role="region" aria-label="Jobs, scrollable table">
			<table class="w-full min-w-[56rem] text-left text-meta">
				<thead>
					<tr class="border-b border-rule">
						<th class="axis-label py-2 pr-4 font-normal">Job</th>
						<th class="axis-label py-2 pr-4 font-normal">Score</th>
						<th class="axis-label py-2 pr-4 font-normal">Decision</th>
						<th class="axis-label py-2 pr-4 font-normal">Board</th>
						<th class="axis-label py-2 font-normal"><span class="sr-only">Actions</span></th>
					</tr>
				</thead>
				<tbody>
					{#each rows as row (row.id)}
						<tr class="border-b border-rule align-top">
							<td class="py-3 pr-4">
								<a href="/jobs/{row.id}" target="_blank" rel="noopener noreferrer" class="font-semibold underline-offset-4 hover:underline">{row.title}</a>
								<p class="mt-0.5 text-muted">
									{row.company_name ?? 'No company'}{row.location ? ` · ${row.location}` : ''}
									· <a href={row.url} target="_blank" rel="noopener noreferrer" class="underline underline-offset-4">source</a>
								</p>
							</td>
							<td class="coord py-3 pr-4">{row.relevance_score}</td>
							<td class="py-3 pr-4">{decision(row)}</td>
							<td class="py-3 pr-4">
								{#if !row.is_active}
									<span class="text-muted">Inactive</span>
								{:else if row.on_board}
									On the board
								{:else if row.is_audio_related}
									<span class="text-muted">Hidden, company failing</span>
								{:else}
									<span class="text-muted">Hidden</span>
								{/if}
							</td>
							<td class="py-3">
								<div class="flex flex-wrap justify-end gap-2">
									{#if row.is_audio_related_override !== true}
										<button type="button" class="btn btn-primary" disabled={busyId === row.id} onclick={() => setAudio(row, true)}>
											Show on board
										</button>
									{/if}
									{#if row.is_audio_related_override !== false}
										<button type="button" class="btn btn-quiet" disabled={busyId === row.id} onclick={() => setAudio(row, false)}>
											Hide as not audio
										</button>
									{/if}
									{#if row.is_audio_related_override !== null}
										<button type="button" class="btn btn-quiet" disabled={busyId === row.id} onclick={() => setAudio(row, null)}>
											Back to score
										</button>
									{/if}
								</div>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>

		<div class="mt-6 flex items-center justify-center gap-3">
			<button type="button" class="btn btn-quiet" disabled={page <= 1} onclick={() => go(-1)}><svg width="12" height="12" viewBox="0 0 16 16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M13 8H3M7 4L3 8l4 4"/></svg>Prev</button>
			<span class="coord text-muted">Page {pageData.page} of {pageData.pages} · {pageData.total} jobs</span>
			<button type="button" class="btn btn-quiet" disabled={page >= pageData.pages} onclick={() => go(1)}>Next<svg width="12" height="12" viewBox="0 0 16 16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M3 8h10M9 4l4 4-4 4"/></svg></button>
		</div>
	{/if}
</section>
