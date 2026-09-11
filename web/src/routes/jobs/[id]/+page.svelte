<script lang="ts">
	import { formatDate, formatSalary, timeAgo } from '$lib/format';
	import { serializeJsonLd } from '$lib/jsonld';
	import { JOB_FEEDBACK_KINDS } from '$lib/feedback';
	import FeedbackDialog from '$lib/components/FeedbackDialog.svelte';

	let { data } = $props();

	const job = $derived(data.job);
	const salary = $derived(formatSalary(job.salary_min, job.salary_max, job.salary_currency));

	const categoryNames = $derived.by(() => {
		const map = new Map<string, string>();
		for (const c of data.categories ?? []) map.set(c.id, c.name);
		return map;
	});

	const categoryOptions = $derived((data.categories ?? []).map((c) => ({ id: c.id, name: c.name })));

	let reportOpen = $state(false);
</script>

<svelte:head>
	<title>{data.meta.title}</title>
	<meta name="description" content={data.meta.description} />
	<link rel="canonical" href="{data.siteUrl}/jobs/{job.id}" />
	{@html `<script type="application/ld+json">${serializeJsonLd(data.jsonLd)}<\/script>`}
</svelte:head>

<nav aria-label="Breadcrumb" class="mt-6 coord text-muted">
	<a href="/jobs" class="hover:text-accent">Jobs</a>
	<span aria-hidden="true"> / </span>
	{#if job.company}
		<span class="text-ink">{job.company.name}</span>
	{:else}
		<span class="text-ink">Listing</span>
	{/if}
</nav>

<div class="mt-3 grid gap-6 lg:grid-cols-[1fr_18rem]">
	<article class="min-w-0">
		<header class="pb-6">
			<h1 class="text-display leading-tight font-semibold tracking-tight text-balance">{job.title}</h1>
			<p class="mt-2 text-meta font-semibold text-muted">
				{#if job.company}{job.company.name}{/if}
				{#if job.location}<span aria-hidden="true"> · </span>{job.location}{/if}
				{#if job.remote}<span aria-hidden="true"> · </span><span class="text-ink">Remote OK</span>{/if}
			</p>
		</header>

		<dl
			class="coord grid grid-cols-2 gap-x-6 gap-y-3 border-y border-rule py-5 sm:grid-cols-4"
		>
			<div>
				<dt class="axis-label">Salary</dt>
				<dd class="mt-0.5 font-semibold">{salary || '—'}</dd>
			</div>
			<div>
				<dt class="axis-label">Type</dt>
				<dd class="mt-0.5">{job.job_type || '—'}</dd>
			</div>
			<div>
				<dt class="axis-label">Level</dt>
				<dd class="mt-0.5">{job.seniority ?? '—'}</dd>
			</div>
			<div>
				<dt class="axis-label">Posted</dt>
				<dd class="mt-0.5">{timeAgo(job.posted_date ?? job.scraped_at)}</dd>
			</div>
		</dl>

		{#if job.job_categories.length > 0}
			<ul class="flex flex-wrap gap-x-4 gap-y-2 border-b border-rule py-4" aria-label="Specialties">
				{#each job.job_categories as cat (cat)}
					<li>
						<a
							href="/jobs?category={cat}"
							class="coord text-muted underline decoration-rule underline-offset-4 hover:text-accent hover:decoration-accent"
						>
							{categoryNames.get(cat) ?? cat.replaceAll('_', ' ')}
						</a>
					</li>
				{/each}
			</ul>
		{/if}

		<div class="py-7">
			{#if data.description}
				<div class="job-description max-w-none space-y-3 text-[15px] leading-relaxed [&_h2]:mt-6 [&_h2]:text-title [&_h2]:font-bold [&_h3]:mt-4 [&_h3]:font-bold [&_li]:ml-5 [&_p]:min-h-4 [&_ul]:list-disc">
					{@html data.description}
				</div>
			{:else if data.plainDescription}
				<p class="max-w-none whitespace-pre-line text-[15px] leading-relaxed">
					{data.plainDescription}
				</p>
			{:else}
				<p class="text-meta text-muted">
					The employer didn't include a description — follow the link to see the full posting.
				</p>
			{/if}

			<p class="coord mt-8 border-t border-rule pt-4 text-muted">
				Scraped {formatDate(job.scraped_at)}
				{#if job.source === 'community'}
					· <span class="font-bold">Community submission, reviewed by moderators</span>
					{#if job.expires_date}· expires {formatDate(job.expires_date)}{/if}
				{/if}
			</p>
		</div>
	</article>

	<aside class="flex h-fit flex-col gap-3 lg:sticky lg:top-20">
		<a
			href={job.url}
			target="_blank"
			rel="noopener noreferrer"
			class="btn btn-primary w-full !py-3.5 !text-base"
		>
			Apply at source<svg width="11" height="11" viewBox="0 0 16 16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M6 3h7v7M13 3L6.5 9.5M11 11v2H3V5h2"/></svg>
		</a>
		<p class="coord leading-relaxed text-muted">
			This listing links directly to the employer's site. ASoundJob never takes a cut
			or stands between you and the application.
		</p>
		{#if job.company}
			<div class="p-4">
				<p class="text-meta font-bold">About the company</p>
				<p class="mt-2 text-title font-bold">{job.company.name}</p>
				<a
					href="/companies/{job.company.slug}"
					class="mt-1 inline-block coord font-semibold text-accent hover:underline"
				>
					View company page →
				</a>
			</div>
		{/if}
		<div class="p-4">
			<p class="text-meta font-bold">See a problem?</p>
			<p class="mt-2 text-meta text-muted">
				Flag a category mistake, a broken link, or anything else off about this listing.
			</p>
			<button type="button" class="btn btn-quiet mt-3 w-full" onclick={() => (reportOpen = true)}>
				Report an issue
			</button>
		</div>
	</aside>
</div>

<FeedbackDialog
	mode="job"
	jobId={job.id}
	jobTitle={job.title}
	kinds={JOB_FEEDBACK_KINDS}
	categories={categoryOptions}
	bind:open={reportOpen}
/>
