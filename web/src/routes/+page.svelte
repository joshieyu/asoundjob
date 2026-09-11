<script lang="ts">
	import JobStrip from '$lib/components/JobStrip.svelte';
	import FeedbackDialog from '$lib/components/FeedbackDialog.svelte';
	import { JOB_FEEDBACK_KINDS } from '$lib/feedback';
	import type { Job } from '$lib/types';

	let { data } = $props();

	const total = $derived(data.totalJobs);
	const featured = $derived(data.featured?.items ?? []);
	const categoryMeta = $derived(data.categories?.categories ?? []);
	const openCategories = $derived(
		[...categoryMeta]
			.map((c) => ({ ...c, count: c.job_count }))
			.filter((c) => c.count > 0)
			.sort((a, b) => b.count - a.count)
	);
	const visibleSpecialtyChips = $derived(openCategories.slice(0, 12));
	const moreSpecialtyCount = $derived(Math.max(0, openCategories.length - 12));

	const categoryNames = $derived.by(() => {
		const map = new Map<string, string>();
		for (const c of categoryMeta) map.set(c.id, c.name);
		return map;
	});

	const categoryOptions = $derived(categoryMeta.map((c) => ({ id: c.id, name: c.name })));

	const reportKinds = JOB_FEEDBACK_KINDS.filter(
		(k) => k.value === 'wrong_category' || k.value === 'not_audio'
	);

	let reportJob = $state<Job | null>(null);
	let reportOpen = $state(false);

	function onReport(job: Job) {
		reportJob = job;
		reportOpen = true;
	}
</script>

<svelte:head>
	<title>{data.meta.title}</title>
	<meta name="description" content={data.meta.description} />
	<link rel="canonical" href="{data.siteUrl}/" />
</svelte:head>

<section class="mt-10 sm:mt-16" aria-labelledby="hero-heading">
	<h1 id="hero-heading" class="sr-only">Audio industry jobs</h1>

	<p class="specimen">{total.toLocaleString('en-US')}</p>
	<p class="mt-3 text-display leading-tight font-light text-balance">
		open audio roles, re&#8288;-read every night.
	</p>
	<p class="coord mt-4 text-muted">
		{categoryMeta.length} specialties · verified companies only
	</p>

	<form action="/jobs" method="get" role="search" class="mt-10 flex max-w-2xl flex-col gap-3 sm:flex-row">
		<label class="sr-only" for="q">Search jobs</label>
		<input
			id="q"
			name="q"
			type="search"
			placeholder="Search titles, skills, companies…"
			class="field flex-1"
		/>
		<button type="submit" class="btn btn-primary shrink-0">Find jobs</button>
	</form>

	{#if openCategories.length > 0}
		<div class="mt-12">
			<h2 class="axis-label">Browse by specialty</h2>
			<ul class="mt-4 grid gap-x-8 gap-y-2 sm:grid-cols-2 lg:grid-cols-3">
				{#each visibleSpecialtyChips as cat (cat.id)}
					<li>
						<a
							href="/jobs?category={cat.id}"
							class="group flex items-baseline gap-3 py-1 hover:text-accent"
						>
							<span class="min-w-0 flex-1 truncate text-meta font-semibold group-hover:underline"
								>{cat.name}</span
							>
							<span class="coord shrink-0 text-muted">{cat.count}</span>
						</a>
					</li>
				{/each}
			</ul>
			<p class="mt-5 flex flex-wrap items-center gap-x-6 gap-y-2">
				{#if moreSpecialtyCount > 0}
					<a href="/jobs" class="link text-meta font-semibold">{moreSpecialtyCount} more specialties</a>
				{/if}
				<a href="/jobs" class="link text-meta font-semibold">All {total.toLocaleString('en-US')} roles</a>
			</p>
		</div>
	{/if}
</section>

<section class="mt-20" aria-labelledby="featured-heading">
	<div class="flex items-end justify-between gap-4 border-b border-rule pb-3">
		<h2 id="featured-heading" class="text-title font-semibold">Fresh on the board</h2>
		<a href="/jobs" class="link text-meta font-semibold whitespace-nowrap">
			Browse all {total.toLocaleString('en-US')}
		</a>
	</div>

	<div class="@container mt-4">
		<div class="grid items-stretch gap-3 @3xl:grid-cols-2">
		{#each featured as job (job.id)}
			<JobStrip {job} {categoryNames} {onReport} />
		{:else}
			<p class="col-span-full py-10 text-meta text-muted" role={data.boardUnavailable ? 'alert' : undefined}>
				{data.boardUnavailable
					? "We couldn't read the board just now — the listings service didn't answer. Refresh in a moment."
					: 'No listings to show yet.'}
			</p>
		{/each}
		</div>
	</div>
</section>

<section class="mt-20 grid gap-10 sm:grid-cols-3" aria-labelledby="why-heading">
	<h2 id="why-heading" class="sr-only">Why ASoundJob</h2>
	<div>
		<h3 class="text-title font-semibold">Refreshed, not stale</h3>
		<p class="mt-2 text-meta text-muted">
			A scraper re-checks every verified company's careers page each night. When a
			job disappears from the source, it disappears here.
		</p>
	</div>
	<div>
		<h3 class="text-title font-semibold">{categoryMeta.length} audio specialties</h3>
		<p class="mt-2 text-meta text-muted">
			DSP, live sound, acoustics, transducers, game audio — filter by the work you
			actually do, not keyword soup.
		</p>
	</div>
	<div>
		<h3 class="text-title font-semibold">Community reviewed</h3>
		<p class="mt-2 text-meta text-muted">
			Every community submission is approved by a human moderator before it goes
			live, and expires after a month.
		</p>
	</div>
</section>

<section class="mt-20 flex flex-col items-start justify-between gap-6 border-t border-rule pt-10 sm:flex-row sm:items-center">
	<div>
		<h2 class="text-display font-light">Hiring in audio?</h2>
		<p class="mt-2 max-w-lg text-meta text-muted">
			Put your opening in front of the people who speak this language. Submissions
			are free and reviewed by the Young Audio Professionals community within days.
		</p>
	</div>
	<a href="/jobs/submit" class="btn btn-primary shrink-0">Submit a job</a>
</section>

{#if reportJob}
	<FeedbackDialog
		mode="job"
		jobId={reportJob.id}
		jobTitle={reportJob.title}
		kinds={reportKinds}
		categories={categoryOptions}
		bind:open={reportOpen}
	/>
{/if}
