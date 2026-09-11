<script lang="ts">
	import type { Job } from '$lib/types';
	import { formatSalary, timeAgo } from '$lib/format';
	import { bookmarks, hydrateBookmarks } from '$lib/bookmarks.svelte';
	import RecencyTick from './RecencyTick.svelte';

	let {
		job,
		categoryNames = new Map<string, string>(),
		maxAgeDays = 90,
		onReport
	}: {
		job: Job;
		categoryNames?: Map<string, string>;
		maxAgeDays?: number;
		onReport?: (job: Job) => void;
	} = $props();

	$effect(() => {
		hydrateBookmarks();
	});

	const bookmarked = $derived(bookmarks.has(job.id));
	const salary = $derived(formatSalary(job.salary_min, job.salary_max, job.salary_currency));
	const seenAt = $derived(job.posted_date ?? job.scraped_at);
	const ageDays = $derived.by(() => {
		if (!seenAt) return null;
		const then = new Date(seenAt).getTime();
		if (Number.isNaN(then)) return null;
		return Math.max(0, Math.floor((Date.now() - then) / 86_400_000));
	});
	const specialties = $derived(
		job.job_categories.map((c) => categoryNames.get(c) ?? c.replaceAll('_', ' '))
	);
</script>

<article class="group grid grid-cols-[1fr_auto] gap-x-4 py-7 transition-colors">
	<div class="min-w-0">
		<h3 class="text-title font-semibold leading-tight text-balance">
			<a href="/jobs/{job.id}" class="line-clamp-2 hover:text-accent hover:underline">
				{job.title}
			</a>
		</h3>

		<p class="mt-1 text-meta text-muted">
			{#if job.company}
				<span class="font-semibold text-ink">{job.company.name}</span>
				<span aria-hidden="true"> · </span>
			{/if}
			{job.location ?? 'Location not listed'}{job.remote ? ' · Remote' : ''}
		</p>

		<dl
			class="coord mt-3 grid grid-cols-[minmax(0,8rem)_minmax(0,1fr)] gap-x-4 gap-y-1 sm:grid-cols-[minmax(0,9rem)_minmax(0,6rem)_minmax(0,1fr)]"
		>
			<dt class="sr-only">Salary</dt>
			<dd class="col-start-1" class:text-muted={!salary}>{salary || '—'}</dd>

			<dt class="sr-only">Level</dt>
			<dd class="col-start-2">{job.seniority ?? '—'}</dd>

			<dt class="sr-only">Type</dt>
			<dd class="col-start-1 sm:col-start-3">{job.job_type || '—'}</dd>

			{#if job.source === 'community'}
				<dt class="sr-only">Source</dt>
				<dd class="col-span-3 font-bold">community submission</dd>
			{/if}
		</dl>

		{#if specialties.length > 0}
			<p class="mt-2 text-meta text-muted">
				<span class="sr-only">Specialties: </span>{specialties.join(' · ')}
			</p>
		{/if}

		<div class="mt-3 flex items-center gap-3">
			<span class="coord shrink-0 text-muted">{timeAgo(seenAt)}</span>
			<span class="w-28 shrink-0"><RecencyTick days={ageDays} maxDays={maxAgeDays} /></span>
		</div>
	</div>

	<div class="flex shrink-0 items-start gap-1">
		<button
			type="button"
			class="flex h-8 w-8 items-center justify-center border transition-colors {bookmarked ? 'border-ink bg-ink text-ground'
				: 'border-transparent text-muted hover:border-muted hover:text-ink'}"
			aria-pressed={bookmarked}
			aria-label={bookmarked
				? `Remove bookmark from ${job.title}`
				: `Bookmark ${job.title} for later`}
			title="Bookmark for later (saved on this device)"
			onclick={() => bookmarks.toggle(job.id)}
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
			class="flex h-8 w-8 items-center justify-center border border-transparent text-muted transition-colors hover:border-muted hover:text-ink"
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
	</div>
</article>
