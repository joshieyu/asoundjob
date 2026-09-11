<script lang="ts">
	import { clientApi } from '$lib/client';

	interface ScrapeLogEntry {
		id: number;
		status: string;
		jobs_found: number;
		scrape_method: string | null;
		error_message: string | null;
		started_at: string;
	}

	interface ScrapeStatus {
		running: boolean;
		last_finished_at: string | null;
		recent: ScrapeLogEntry[];
	}

	let status = $state<ScrapeStatus | null>(null);
	let limit = $state<number | null>(null);
	let message = $state('');
	let triggering = $state(false);

	async function refresh() {
		try {
			status = await clientApi<ScrapeStatus>('/api/admin/scrape/status');
		} catch {
			/* transient */
		}
	}

	$effect(() => {
		refresh();
		const interval = setInterval(refresh, 5000);
		return () => clearInterval(interval);
	});

	async function trigger() {
		triggering = true;
		message = '';
		try {
			await clientApi('/api/admin/scrape', {
				method: 'POST',
				body: undefined,
			});
			message = 'Scrape cycle started.';
			await refresh();
		} catch (err) {
			message = err instanceof Error ? err.message : 'Failed to start';
		} finally {
			triggering = false;
		}
	}
</script>

<section class="mt-10">
	<h1 class="text-title font-semibold">Scraper control</h1>

	<div class="mt-6 flex flex-wrap items-center gap-x-8 gap-y-4">
		<div class="flex items-center gap-2.5">
			<span
				class="inline-block h-3 w-3 rounded-full border transition-colors {status?.running ? 'animate-pulse border-accent bg-accent'
					: 'border-muted bg-transparent'}"
			></span>
			<span class="coord">
				{status?.running ? 'Cycle running' : 'Idle'}
			</span>
		</div>

		<label class="flex items-center gap-2 text-meta font-semibold">
			Limit companies
			<input type="number" min="1" bind:value={limit} placeholder="all" class="field h-9 w-24" />
		</label>

		<button type="button" class="btn btn-primary" disabled={triggering || (status?.running ?? false)} onclick={trigger}>
			{status?.running ? 'Running…' : 'Start cycle'}
		</button>

		{#if message}<p class="coord" role="status">{message}</p>{/if}
	</div>

	<h2 class="mt-14 text-title font-semibold">Recent activity</h2>
	<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
	<div
		class="mt-4 overflow-x-auto"
		tabindex="0"
		role="region"
		aria-label="Recent scrape activity, scrollable table"
	>
		<table class="coord w-full min-w-[36rem] text-left">
			<caption class="sr-only">The 15 most recent scrape cycles, with method, status, jobs found and any error</caption>
			<thead>
				<tr class="border-b border-muted text-muted">
					<th scope="col" class="px-4 py-2.5 font-medium">Started</th>
					<th scope="col" class="px-4 py-2.5 font-medium">Method</th>
					<th scope="col" class="px-4 py-2.5 font-medium">Status</th>
					<th scope="col" class="px-4 py-2.5 font-medium">Jobs</th>
					<th scope="col" class="px-4 py-2.5 font-medium">Error</th>
				</tr>
			</thead>
			<tbody>
				{#each status?.recent.slice(0, 15) ?? [] as entry (entry.id)}
					<tr class="border-b border-rule last:border-0">
						<td class="px-4 py-2">{new Date(entry.started_at).toLocaleString()}</td>
						<td class="px-4 py-2">{entry.scrape_method ?? '—'}</td>
						<td class="px-4 py-2">
							<span class={entry.status === 'success' ? '' : 'font-semibold'}>
								{entry.status}
							</span>
						</td>
						<td class="px-4 py-2 tabular-nums">{entry.jobs_found}</td>
						<td class="max-w-[16rem] truncate px-4 py-2 text-muted" title={entry.error_message ?? ''}>
							{entry.error_message ?? '—'}
						</td>
					</tr>
				{:else}
					<tr><td colspan="5" class="px-4 py-4 text-muted">No scrape activity yet.</td></tr>
				{/each}
			</tbody>
		</table>
	</div>
</section>
