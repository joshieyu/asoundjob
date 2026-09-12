<script lang="ts">
	import JobStrip from '$lib/components/JobStrip.svelte';
	import CompanySuggestionDialog from '$lib/components/CompanySuggestionDialog.svelte';

	let { data } = $props();

	const company = $derived(data.company);

	let suggestOpen = $state(false);
</script>

<svelte:head>
	<title>{data.meta.title}</title>
	<meta name="description" content={data.meta.description} />
	<link rel="canonical" href="{data.siteUrl}/companies/{company.slug}" />
</svelte:head>

<header class="mt-6 border-b border-rule pb-6">
	<h1 class="text-display leading-tight font-semibold tracking-tight text-balance">
		{company.name}
	</h1>
	<p class="mt-2 text-meta font-semibold text-muted">
		{company.category}
		<span aria-hidden="true"> · </span>
		{company.board_jobs_count} {company.board_jobs_count === 1 ? 'open role' : 'open roles'}
	</p>
	{#if company.headquarters || company.founded}
		<p class="mt-1 coord text-muted">
			{#if company.headquarters}{company.headquarters}{/if}
			{#if company.headquarters && company.founded}<span aria-hidden="true"> · </span>{/if}
			{#if company.founded}Founded {company.founded}{/if}
		</p>
	{/if}
	<div class="mt-4 flex flex-wrap gap-2">
		{#if company.careers_url}
			<a
				href={company.careers_url}
				target="_blank"
				rel="noopener noreferrer"
				class="btn btn-primary"
			>
				Careers page<span class="sr-only"> (opens in a new tab)</span>
			</a>
		{/if}
		{#if company.website_url}
			<a
				href={company.website_url}
				target="_blank"
				rel="noopener noreferrer"
				class="btn btn-quiet"
			>
				Website<span class="sr-only"> (opens in a new tab)</span>
			</a>
		{/if}
		<button type="button" class="btn btn-quiet" onclick={() => (suggestOpen = true)}>
			Suggest an edit
		</button>
	</div>
</header>

{#if company.description}
	<div class="border-b border-rule py-6">
		<p class="max-w-[68ch] text-body leading-relaxed whitespace-pre-line">
			{company.description}
		</p>
	</div>
{/if}

{#if company.community_links && company.community_links.length > 0}
	<div class="border-b border-rule py-6">
		<h2 class="axis-label">Links</h2>
		<ul class="mt-2 flex flex-col gap-1.5">
			{#each company.community_links as communityLink, i (i)}
				<li class="min-w-0">
					<a
						href={communityLink.url}
						target="_blank"
						rel="noopener noreferrer"
						class="link wrap-anywhere"
					>
						{communityLink.label}<span class="sr-only"> (opens in a new tab)</span>
					</a>
				</li>
			{/each}
		</ul>
	</div>
{/if}

<div class="py-6">
	<h2 class="axis-label mb-3">Open roles</h2>
	{#if company.jobs.length > 0}
		<div class="grid gap-4 sm:grid-cols-2">
			{#each company.jobs as job (job.id)}
				<JobStrip {job} />
			{/each}
		</div>
	{:else}
		<p class="text-meta text-muted">
			No open roles listed for {company.name} right now.
			<a href="/jobs" class="link">Browse all jobs</a>.
		</p>
	{/if}
</div>

<CompanySuggestionDialog slug={company.slug} companyName={company.name} bind:open={suggestOpen} />
