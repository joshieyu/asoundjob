<script lang="ts">
	import { formatDate, formatSalary, timeAgo } from '$lib/format';
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
	<link rel="canonical" href="http://localhost:5173/jobs/{job.id}" />
	{@html `<script type="application/ld+json">${JSON.stringify(data.jsonLd)}<\/script>`}
</svelte:head>

<nav aria-label="Breadcrumb" class="mt-6 font-mono text-xs tracking-wide text-ink-soft">
	<a href="/jobs" class="hover:text-fader-deep">JOBS</a>
	<span aria-hidden="true"> / </span>
	{#if job.company}
		<span class="text-ink">{job.company.name}</span>
	{:else}
		<span class="text-ink">Listing</span>
	{/if}
</nav>

<div class="mt-3 grid gap-6 lg:grid-cols-[1fr_18rem]">
	<article class="panel min-w-0">
		<header class="border-b border-seam bg-panel-recessed px-5 py-4 sm:px-7 sm:py-5">
			<h1 class="text-xl font-black tracking-tight text-balance sm:text-3xl">{job.title}</h1>
			<p class="mt-1.5 text-sm font-semibold text-ink-soft">
				{#if job.company}{job.company.name}{/if}
				{#if job.location}<span aria-hidden="true"> · </span>{job.location}{/if}
				{#if job.remote}<span aria-hidden="true"> · </span><span class="text-lit">Remote OK</span>{/if}
			</p>
		</header>

		<dl
			class="grid grid-cols-2 gap-x-4 gap-y-2 border-b border-seam px-5 py-4 font-mono text-xs sm:grid-cols-4 sm:px-7"
		>
			<div>
				<dt class="tracking-[0.12em] text-ink-soft uppercase">Salary</dt>
				<dd class="mt-0.5 font-semibold">{salary || '—'}</dd>
			</div>
			<div>
				<dt class="tracking-[0.12em] text-ink-soft uppercase">Type</dt>
				<dd class="mt-0.5">{job.job_type ?? '—'}</dd>
			</div>
			<div>
				<dt class="tracking-[0.12em] text-ink-soft uppercase">Level</dt>
				<dd class="mt-0.5">{job.seniority ?? '—'}</dd>
			</div>
			<div>
				<dt class="tracking-[0.12em] text-ink-soft uppercase">Posted</dt>
				<dd class="mt-0.5">{timeAgo(job.posted_date ?? job.scraped_at)}</dd>
			</div>
		</dl>

		{#if job.job_categories.length > 0}
			<ul class="flex flex-wrap gap-1.5 border-b border-seam px-5 py-3 sm:px-7" aria-label="Specialties">
				{#each job.job_categories as cat (cat)}
					<li>
						<a
							href="/jobs?category={cat}"
							class="rounded-sm border border-seam bg-panel-recessed px-1.5 py-0.5 font-mono text-[10px] tracking-wide text-ink-soft hover:border-fader hover:text-fader-deep"
						>
							{categoryNames.get(cat) ?? cat.replaceAll('_', ' ')}
						</a>
					</li>
				{/each}
			</ul>
		{/if}

		<div class="px-5 py-6 sm:px-7">
			{#if data.description}
				<div class="job-description max-w-none space-y-3 text-[15px] leading-relaxed [&_h2]:mt-6 [&_h2]:text-lg [&_h2]:font-bold [&_h3]:mt-4 [&_h3]:font-bold [&_li]:ml-5 [&_p]:min-h-4 [&_ul]:list-disc">
					{@html data.description}
				</div>
			{:else if data.plainDescription}
				<p class="max-w-none whitespace-pre-line text-[15px] leading-relaxed">
					{data.plainDescription}
				</p>
			{:else}
				<p class="text-sm text-ink-soft">
					The employer didn't include a description — follow the link to see the full posting.
				</p>
			{/if}

			<p class="mt-8 border-t border-seam pt-4 font-mono text-[11px] tracking-wide text-ink-soft">
				Scraped {formatDate(job.scraped_at)}
				{#if job.source === 'community'}
					· <span class="text-fader-deep">Community submission, reviewed by moderators</span>
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
			class="btn-primary w-full !py-3.5 !text-base"
		>
			Apply at source ↗
		</a>
		<p class="well p-3 font-mono text-[11px] leading-relaxed tracking-wide text-ink-soft">
			This listing links directly to the employer's site. ASoundJob never takes a cut
			or stands between you and the application.
		</p>
		{#if job.company}
			<div class="panel p-4">
				<p class="legend">ABOUT THE COMPANY</p>
				<p class="mt-2 text-lg font-bold">{job.company.name}</p>
				<a
					href="/companies/{job.company.slug}"
					class="mt-1 inline-block font-mono text-xs font-semibold text-fader-deep hover:underline"
				>
					View company page →
				</a>
			</div>
		{/if}
		<div class="panel p-4">
			<p class="legend">SEE A PROBLEM?</p>
			<p class="mt-2 text-sm text-ink-soft">
				Flag a category mistake, a broken link, or anything else off about this listing.
			</p>
			<button type="button" class="btn-latch mt-3 w-full" onclick={() => (reportOpen = true)}>
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
