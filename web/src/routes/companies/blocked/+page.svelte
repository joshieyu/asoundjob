<script lang="ts">
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	// `blocked` is null when the API call failed — an unknown list, not an empty one.
	const blocked = $derived(data.blocked);
</script>

<svelte:head>
	<title>Companies we can't scrape | ASoundJob</title>
	<meta
		name="description"
		content="Audio companies whose careers pages block automated readers — their roles never reach this board, so it's worth checking them directly."
	/>
	<link rel="canonical" href="{data.siteUrl}/companies/blocked" />
</svelte:head>

<div class="mx-auto mt-16 mb-32 max-w-3xl sm:mt-24">
	<h1 class="text-display font-light tracking-tight text-balance">
		Companies our scraper can't read.
	</h1>

	<div class="mt-12 max-w-[68ch] space-y-6 text-body leading-relaxed">
		<p>
			These are companies we've checked by hand and can't read. Some refuse automated readers
			outright — a bot block, a captcha, a flat 403. Some draw their whole job board with
			JavaScript, or bury it in an embedded portal we can't follow. Either way our scraper comes
			back with nothing, so roles at these companies never reach this board.
		</p>
		<p>
			We're not saying any of them are hiring right now — we can't tell either way, and that's
			the point. These are real audio companies worth watching, and their careers pages open
			perfectly well in a normal browser. If one of them is a fit, go look for yourself.
		</p>
	</div>

	<div class="mt-16 max-w-[68ch]">
		<p class="text-body leading-relaxed">
			Searching <strong class="font-semibold">"acoustic engineer"</strong> on LinkedIn surfaces a
			lot of roles that never make it onto a company's own careers page, blocked or not.
		</p>
		<a
			href="https://www.linkedin.com/jobs/search/?keywords=acoustic%20engineer"
			target="_blank"
			rel="noopener noreferrer"
			class="btn btn-quiet mt-6"
		>
			Search LinkedIn<svg width="11" height="11" viewBox="0 0 16 16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M6 3h7v7M13 3L6.5 9.5M11 11v2H3V5h2"/></svg>
		</a>
	</div>

	<section class="mt-24" aria-labelledby="blocked-companies-heading">
		<h2 id="blocked-companies-heading" class="text-title font-medium tracking-tight">
			Blocked companies
		</h2>

		{#if !blocked}
			<p class="mt-4 max-w-[68ch] text-body leading-relaxed text-muted">
				We couldn't load this list right now. Refresh in a moment and it should come back.
			</p>
		{:else if blocked.total > 0}
			<p class="coord mt-3 text-muted">
				{blocked.total} companies worth checking yourself
			</p>

			<ul class="mt-8 border-t border-rule">
				{#each blocked.companies as company (company.id)}
					<li
						class="flex items-baseline justify-between gap-4 border-b border-rule py-3"
					>
						<span class="min-w-0">
							<span class="block truncate font-medium">{company.name}</span>
							<span class="axis-label mt-0.5 block truncate">{company.category}</span>
						</span>
						{#if company.careers_url}
							<a
								href={company.careers_url}
								target="_blank"
								rel="noopener noreferrer"
								class="link shrink-0 text-meta"
							>
								Careers<svg width="11" height="11" viewBox="0 0 16 16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M6 3h7v7M13 3L6.5 9.5M11 11v2H3V5h2"/></svg>
							</a>
						{/if}
					</li>
				{/each}
			</ul>
		{:else}
			<p class="mt-4 max-w-[68ch] text-body leading-relaxed text-muted">
				Nothing is currently on this list — every company we track is readable right now.
			</p>
		{/if}
	</section>
</div>
