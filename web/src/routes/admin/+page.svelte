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
	<p class="mt-10 text-meta font-semibold text-ink" role="alert">{error}</p>
{:else if !stats}
	<p class="mt-10 text-meta text-muted">Loading…</p>
{:else}
	<dl class="mt-10 grid grid-cols-2 gap-x-6 gap-y-8 sm:grid-cols-3 lg:grid-cols-5">
		{#each cards as [label, value] (label)}
			<div class="flex flex-col-reverse">
				<dt class="axis-label mt-1">{label}</dt>
				<dd class="text-title font-semibold tabular-nums">{value.toLocaleString('en-US')}</dd>
			</div>
		{/each}
	</dl>

	<section class="mt-14">
		<h2 class="text-title font-semibold">Jobs by level</h2>
		<dl class="mt-4 flex flex-wrap gap-x-8 gap-y-4">
			{#each Object.entries(stats.jobs_by_seniority) as [level, count] (level)}
				<div>
					<dt class="axis-label">{level}</dt>
					<dd class="mt-0.5 text-meta font-semibold tabular-nums">{count}</dd>
				</div>
			{/each}
		</dl>
		<p class="mt-6 text-meta text-muted">
			Last scrape started: {stats.last_scrape_at ? new Date(stats.last_scrape_at).toLocaleString() : 'never'}
		</p>
	</section>

	<section class="mt-14">
		<h2 class="text-title font-semibold">User feedback</h2>
		<p class="mt-2 max-w-prose text-meta text-muted">
			Review reported job listings and general site feedback from visitors.
		</p>
		<a href="/admin/feedback" class="btn btn-quiet mt-4">Open feedback queue<svg width="12" height="12" viewBox="0 0 16 16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M3 8h10M9 4l4 4-4 4"/></svg></a>
	</section>
{/if}
