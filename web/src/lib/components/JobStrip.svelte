<script lang="ts">
	import type { Job } from '$lib/types';
	import { formatSalary, timeAgo } from '$lib/format';
	import { bookmarks, hydrateBookmarks } from '$lib/bookmarks.svelte';

	let {
		job,
		categoryNames = new Map<string, string>(),
		onReport
	}: {
		job: Job;
		categoryNames?: Map<string, string>;
		onReport?: (job: Job) => void;
	} = $props();

	$effect(() => {
		hydrateBookmarks();
	});

	const bookmarked = $derived(bookmarks.has(job.id));
	const salary = $derived(formatSalary(job.salary_min, job.salary_max, job.salary_currency));
	const seenAt = $derived(job.posted_date ?? job.scraped_at);
	const specialties = $derived(
		job.job_categories.map((c) => categoryNames.get(c) ?? c.replaceAll('_', ' '))
	);
</script>

<article
	class="group flex flex-col border border-rule bg-ground p-4 transition-colors hover:border-muted sm:p-5"
>
	<div class="flex items-start gap-2">
		<h3 class="min-w-0 flex-1 text-title font-semibold leading-tight text-balance">
			<a href="/jobs/{job.id}" class="line-clamp-2 hover:text-accent hover:underline">
				{job.title}
			</a>
		</h3>

		<div class="-mt-1 -mr-1 flex shrink-0 items-start gap-1">
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
	</div>

	<p class="mt-1 text-meta text-muted">
		{#if job.company}
			<span class="font-semibold text-ink">{job.company.name}</span>
			<span aria-hidden="true"> · </span>
		{/if}
		{job.location ?? 'Location not listed'}{job.remote ? ' · Remote' : ''}
	</p>

	<dl class="mt-3 flex flex-wrap items-baseline gap-x-4 gap-y-1">
		{#if salary}
			<div class="flex items-baseline gap-1.5">
				<dt class="axis-label">sal</dt>
				<dd class="coord">{salary}</dd>
			</div>
		{/if}
		{#if job.seniority}
			<div class="flex items-baseline gap-1.5">
				<dt class="axis-label">lvl</dt>
				<dd class="coord">{job.seniority}</dd>
			</div>
		{/if}
		{#if job.job_type}
			<div class="flex items-baseline gap-1.5">
				<dt class="axis-label">type</dt>
				<dd class="coord">{job.job_type}</dd>
			</div>
		{/if}
		<div class="flex items-baseline gap-1.5">
			<dt class="axis-label">seen</dt>
			<dd class="coord">{timeAgo(seenAt)}</dd>
		</div>
		{#if job.source === 'community'}
			<div class="flex items-baseline gap-1.5">
				<dt class="sr-only">Source</dt>
				<dd class="coord font-bold">community submission</dd>
			</div>
		{/if}
	</dl>

	{#if specialties.length > 0}
		<ul class="mt-auto flex flex-wrap gap-1.5 pt-3" aria-label="Specialties">
			{#each specialties as name (name)}
				<li class="coord border border-rule bg-ground-tint px-1.5 py-0.5 text-muted">{name}</li>
			{/each}
		</ul>
	{/if}
</article>
