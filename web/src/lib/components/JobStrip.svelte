<script lang="ts">
	import type { Job } from '$lib/types';
	import { formatSalary, timeAgo } from '$lib/format';
	import { getBookmarks, toggleBookmark } from '$lib/client';
	import LedMeter from './LedMeter.svelte';

	let {
		job,
		companyMaxSalary = 220000,
		categoryNames = new Map<string, string>(),
		onReport
	}: {
		job: Job;
		companyMaxSalary?: number;
		categoryNames?: Map<string, string>;
		onReport?: (job: Job) => void;
	} = $props();

	let bookmarked = $state(false);

	$effect(() => {
		bookmarked = getBookmarks().has(job.id);
	});

	function onBookmark() {
		bookmarked = toggleBookmark(job.id);
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

	<div class="min-w-0 flex-1 p-4 pb-9 pr-9">
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
						{categoryNames.get(cat) ?? cat.replaceAll('_', ' ')}
					</li>
				{/each}
			</ul>
		{/if}
	</div>

	<button
		type="button"
		class="absolute right-2 top-2 flex h-7 w-7 items-center justify-center rounded-sm border border-seam transition-colors {bookmarked
			? 'border-fader-deep bg-fader text-white'
			: 'bg-panel-raised text-ink-soft hover:text-fader-deep'}"
		aria-pressed={bookmarked}
		aria-label={bookmarked
			? `Remove bookmark from ${job.title}`
			: `Bookmark ${job.title} for later`}
		title="Bookmark for later (saved on this device)"
		onclick={onBookmark}
	>
		<svg width="11" height="14" viewBox="0 0 12 14" aria-hidden="true">
			<path
				d="M2.25 1h7.5a.75.75 0 0 1 .75.75v10.9a.4.4 0 0 1-.62.33L6 10.2l-3.88 2.78a.4.4 0 0 1-.62-.33V1.75A.75.75 0 0 1 2.25 1Z"
				fill={bookmarked ? 'currentColor' : 'none'}
				stroke="currentColor"
				stroke-width="1.3"
				stroke-linejoin="round"
			/>
		</svg>
	</button>

	<button
		type="button"
		class="absolute bottom-2 right-2 flex h-7 w-7 items-center justify-center rounded-sm border border-seam bg-panel-raised text-ink-soft transition-colors hover:text-fader-deep"
		aria-label={`Report an issue with ${job.title}`}
		title="Report an issue with this listing"
		onclick={() => onReport?.(job)}
	>
		<svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
			<path
				d="M8 1 1 14h14L8 1Zm0 4.5c.41 0 .75.34.75.75v3.5a.75.75 0 0 1-1.5 0v-3.5c0-.41.34-.75.75-.75Zm0 6.75a.9.9 0 1 1 0 1.8.9.9 0 0 1 0-1.8Z"
			/>
		</svg>
	</button>
</article>
