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

<section class="mt-6">
	<h1 class="legend">SCRAPER CONTROL</h1>

	<div class="panel mt-4 flex flex-wrap items-center gap-4 p-5">
		<div class="well flex items-center gap-3 px-4 py-3">
			<span
				class="inline-block h-3 w-3 rounded-full transition-colors {status?.running
					? 'animate-pulse bg-lit'
					: 'bg-led-0'}"
			></span>
			<span class="font-mono text-sm font-semibold tracking-wide uppercase">
				{status?.running ? 'Cycle running' : 'Idle'}
			</span>
		</div>

		<label class="flex items-center gap-2 text-sm font-semibold">
			Limit companies
			<input type="number" min="1" bind:value={limit} placeholder="all" class="well h-9 w-24 px-2 font-mono text-sm" />
		</label>

		<button type="button" class="btn-primary" disabled={triggering || (status?.running ?? false)} onclick={trigger}>
			{status?.running ? 'Running…' : 'Start cycle'}
		</button>

		{#if message}<p class="font-mono text-xs tracking-wide" role="status">{message}</p>{/if}
	</div>

	<h2 class="legend mt-8">RECENT ACTIVITY</h2>
	<div class="panel mt-3 overflow-x-auto">
		<table class="w-full min-w-[36rem] text-left font-mono text-xs">
			<thead>
				<tr class="border-b border-seam tracking-[0.12em] text-ink-soft uppercase">
					<th scope="col" class="px-4 py-2.5">Started</th>
					<th scope="col" class="px-4 py-2.5">Method</th>
					<th scope="col" class="px-4 py-2.5">Status</th>
					<th scope="col" class="px-4 py-2.5">Jobs</th>
					<th scope="col" class="px-4 py-2.5">Error</th>
				</tr>
			</thead>
			<tbody>
				{#each status?.recent.slice(0, 15) ?? [] as entry (entry.id)}
					<tr class="border-b border-seam/60 last:border-0">
						<td class="px-4 py-2">{new Date(entry.started_at).toLocaleString()}</td>
						<td class="px-4 py-2">{entry.scrape_method ?? '—'}</td>
						<td class="px-4 py-2">
							<span class={entry.status === 'success' ? 'text-lit' : 'text-fader-deep'}>
								{entry.status}
							</span>
						</td>
						<td class="px-4 py-2">{entry.jobs_found}</td>
						<td class="max-w-[16rem] truncate px-4 py-2 text-ink-soft" title={entry.error_message ?? ''}>
							{entry.error_message ?? '—'}
						</td>
					</tr>
				{:else}
					<tr><td colspan="5" class="px-4 py-4 text-ink-soft">No scrape activity yet.</td></tr>
				{/each}
			</tbody>
		</table>
	</div>
</section>
