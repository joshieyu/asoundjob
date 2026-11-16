<script lang="ts">
	import JobStrip from '$lib/components/JobStrip.svelte';
	import FeedbackDialog from '$lib/components/FeedbackDialog.svelte';
	import { JOB_FEEDBACK_KINDS } from '$lib/feedback';
	import type { Job } from '$lib/types';

	let { data } = $props();

	const total = $derived(data.totalJobs);
	const featuredJobs = $derived(data.featuredJobs ?? []);
	const fresh = $derived(data.fresh ?? []);
	const categoryMeta = $derived(data.categories?.categories ?? []);
	const openCategories = $derived(
		[...categoryMeta]
			.map((c) => ({ ...c, count: c.job_count }))
			.filter((c) => c.count > 0)
			.sort((a, b) => b.count - a.count)
	);
	const visibleSpecialties = $derived(openCategories.slice(0, 12));

	function shortName(name: string): string {
		const rest = name.replace(/^Audio /, '');
		return rest !== name && rest.split(' ').length > 1 ? rest : name;
	}

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

	<p class="text-[clamp(2.25rem,6vw,3.75rem)] leading-tight font-light tracking-tight text-balance">
		<span class="tabular-nums">{total.toLocaleString('en-US')}</span> open audio roles
	</p>

	<form action="/jobs" method="get" role="search" class="mt-8 flex max-w-2xl flex-col gap-3 sm:flex-row">
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
		<div class="mt-10">
			<h2 class="axis-label">Browse by specialty</h2>
			<ul class="mt-3 flex max-w-4xl flex-wrap gap-x-6 gap-y-2 text-meta font-semibold">
				{#each visibleSpecialties as cat (cat.id)}
					<li>
						<a href="/jobs?category={cat.id}" title={cat.name} class="hover:text-accent hover:underline">
							{shortName(cat.name)}
						</a>
					</li>
				{/each}
				<li>
					<a href="/jobs" class="link">All specialties and roles →</a>
				</li>
			</ul>
		</div>
	{/if}
</section>

{#if featuredJobs.length > 0}
	<section class="mt-20" aria-labelledby="featured-heading">
		<div class="flex items-end justify-between gap-4 border-b border-rule pb-3">
			<h2 id="featured-heading" class="text-title font-semibold">Featured</h2>
			<p class="coord text-muted">Picked by the Young Audio Professionals team</p>
		</div>

		<div class="@container mt-4">
			<div class="grid items-stretch gap-3 @3xl:grid-cols-2">
				{#each featuredJobs as job (job.id)}
					<JobStrip {job} {categoryNames} {onReport} />
				{/each}
			</div>
		</div>
	</section>
{/if}

<section class="mt-20" aria-labelledby="fresh-heading">
	<div class="flex items-end justify-between gap-4 border-b border-rule pb-3">
		<h2 id="fresh-heading" class="text-title font-semibold">Fresh on the board</h2>
		<a href="/jobs" class="link text-meta font-semibold whitespace-nowrap">
			Browse all {total.toLocaleString('en-US')}
		</a>
	</div>

	<div class="@container mt-4">
		<div class="grid items-stretch gap-3 @3xl:grid-cols-2">
		{#each fresh as job (job.id)}
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
