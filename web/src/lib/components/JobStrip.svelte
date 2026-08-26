<script lang="ts">
	import type { Job } from '$lib/types';
	import { formatSalary, timeAgo } from '$lib/format';
	import { getFlags, toggleFlag } from '$lib/client';
	import LedMeter from './LedMeter.svelte';

	let {
		job,
		companyMaxSalary = 220000
	}: { job: Job; companyMaxSalary?: number } = $props();

	let flagged = $state(false);

	$effect(() => {
		flagged = getFlags().has(job.id);
	});

	function onFlag() {
		flagged = toggleFlag(job.id);
	}

	const salary = $derived(formatSalary(job.salary_min, job.salary_max, job.salary_currency));
	const meterValue = $derived(job.salary_max ?? job.salary_min ?? null);
</script>

<article
	class="panel relative flex overflow-hidden transition-shadow hover:shadow-[0_2px_8px_rgb(35_38_43/0.12)]"
>
	{#if meterValue}
		<div class="flex items-stretch gap-2 border-r border-seam bg-panel px-1.5 py-3">
			<LedMeter
				value={meterValue}
				max={companyMaxSalary}
				label={salary ? `Salary ${salary}` : 'Salary not listed'}
			/>
		</div>
	{/if}

	<div class="min-w-0 flex-1 p-4">
		<h3 class="text-base font-bold leading-snug sm:text-lg">
			<a href="/jobs/{job.id}" class="hover:text-fader-deep hover:underline">{job.title}</a>
		</h3>
		<p class="mt-0.5 text-sm text-ink-soft">
			{#if job.company}
				<span class="font-semibold text-ink">{job.company.name}</span>
				<span aria-hidden="true"> · </span>
			{/if}
			{job.location ?? 'Location not listed'}{job.remote ? ' · Remote' : ''}
		</p>

		<dl class="mt-3 flex flex-wrap gap-x-5 gap-y-1 font-mono text-[11px] tracking-wide">
			{#if salary}
				<div class="flex gap-1.5">
					<dt class="text-ink-soft">SAL</dt>
					<dd class="font-semibold">{salary}</dd>
				</div>
			{/if}
			{#if job.job_type}
				<div class="flex gap-1.5">
					<dt class="text-ink-soft">TYPE</dt>
					<dd>{job.job_type}</dd>
				</div>
			{/if}
			{#if job.seniority}
				<div class="flex gap-1.5">
					<dt class="text-ink-soft">LVL</dt>
					<dd>{job.seniority}</dd>
				</div>
			{/if}
			{#if job.source === 'community'}
				<div class="flex gap-1.5">
					<dt class="text-fader-deep">◆</dt>
					<dd class="text-fader-deep">Community</dd>
				</div>
			{/if}
			<div class="flex gap-1.5">
				<dt class="text-ink-soft">SEEN</dt>
				<dd>{timeAgo(job.posted_date ?? job.scraped_at)}</dd>
			</div>
		</dl>

		{#if job.job_categories.length > 0}
			<ul class="mt-2.5 flex flex-wrap gap-1.5" aria-label="Specialties">
				{#each job.job_categories.slice(0, 3) as cat (cat)}
					<li class="rounded-sm border border-seam bg-panel-recessed px-1.5 py-0.5 font-mono text-[10px] tracking-wide text-ink-soft">
						{cat.replaceAll('_', ' ')}
					</li>
				{/each}
			</ul>
		{/if}
	</div>

	<button
		type="button"
		class="absolute right-2 top-2 flex h-7 w-7 items-center justify-center rounded-sm border border-seam transition-colors {flagged
			? 'border-fader-deep bg-fader text-white'
			: 'bg-panel-raised text-ink-soft hover:text-fader-deep'}"
		aria-pressed={flagged}
		aria-label={flagged ? `Remove flag from ${job.title}` : `Flag ${job.title} for later`}
		title="Flag for later (saved on this device)"
		onclick={onFlag}
	>
		<svg width="11" height="14" viewBox="0 0 11 14" fill="currentColor" aria-hidden="true">
			<path d="M1 0h1.5v14H1z" />
			<path d="M2.5 1h7l-2 3 2 3h-7z" />
		</svg>
	</button>
</article>
