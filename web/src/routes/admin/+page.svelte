<script lang="ts">
	import { clientApi } from '$lib/client';

	interface Stats {
		total_active_jobs: number;
		total_companies: number;
		verified_companies: number;
		pending_submissions: number;
		jobs_by_seniority: Record<string, number>;
		remote_jobs: number;
		last_scrape_at: string | null;
	}

	let stats = $state<Stats | null>(null);
	let error = $state('');

	$effect(() => {
		clientApi<Stats>('/api/admin/stats')
			.then((s) => (stats = s))
			.catch((e) => (error = e instanceof Error ? e.message : 'Failed to load'));
	});

	const cards = $derived.by(() => {
		if (!stats) return [];
		return [
			['Active jobs', stats.total_active_jobs],
			['Companies', stats.total_companies],
			['Verified', stats.verified_companies],
			['Pending submissions', stats.pending_submissions],
			['Remote jobs', stats.remote_jobs]
		] as const;
	});
</script>

{#if error}
	<p class="panel mt-6 p-4 text-sm font-semibold text-fader-deep" role="alert">{error}</p>
{:else if !stats}
	<p class="mt-6 font-mono text-sm text-ink-soft">Loading console readouts…</p>
{:else}
	<div class="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
		{#each cards as [label, value] (label)}
			<div class="well p-4">
				<p class="readout text-2xl font-semibold">{value.toLocaleString('en-US')}</p>
				<p class="mt-0.5 font-mono text-[10px] tracking-[0.12em] text-ink-soft uppercase">{label}</p>
			</div>
		{/each}
	</div>

	<section class="panel mt-6 p-5">
		<h2 class="legend">JOBS BY LEVEL</h2>
		<div class="mt-3 flex flex-wrap gap-2">
			{#each Object.entries(stats.jobs_by_seniority) as [level, count] (level)}
				<span class="btn-latch !cursor-default !normal-case !tracking-normal">
					{level}
					<span class="rounded-sm border border-seam bg-panel-recessed px-1 font-mono text-[10px]">{count}</span>
				</span>
			{/each}
		</div>
		<p class="mt-4 font-mono text-[11px] tracking-wide text-ink-soft">
			LAST SCRAPE STARTED: {stats.last_scrape_at ? new Date(stats.last_scrape_at).toLocaleString() : 'never'}
		</p>
	</section>

	<section class="panel mt-6 p-5">
		<h2 class="legend">USER FEEDBACK</h2>
		<p class="mt-2 text-sm text-ink-soft">
			Review reported job listings and general site feedback from visitors.
		</p>
		<a href="/admin/feedback" class="btn-latch mt-3">Open feedback queue →</a>
	</section>
{/if}
