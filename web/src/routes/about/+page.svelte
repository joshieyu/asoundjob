<script lang="ts">
	import discordLink from '$lib/data/discord-link.txt?raw';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	const discord = discordLink.trim();
	const companyCount = $derived(
		data.companyCount > 0 ? data.companyCount.toLocaleString('en-US') : null
	);
	const categoryCount = $derived(data.categoryCount > 0 ? String(data.categoryCount) : null);

	// The prose must never contradict the live count rendered further down the page.
	const directoryPhrase = $derived(
		companyCount ? `a directory of ${companyCount} audio companies` : 'a directory of audio companies'
	);
</script>

<svelte:head>
	<title>About | ASoundJob</title>
	<meta
		name="description"
		content="ASoundJob is built by Young Audio Professionals — a peer community for people working in audio."
	/>
	<link rel="canonical" href="{data.siteUrl}/about" />
</svelte:head>

<div class="mx-auto mt-16 mb-32 max-w-3xl sm:mt-24">
	<h1 class="text-display font-light tracking-tight text-balance">
		Built by the community that works in audio.
	</h1>

	<div class="mt-12 max-w-[68ch] space-y-6 text-body leading-relaxed">
		<p>
			ASoundJob exists because audio careers are invisible on generic job boards. A
			DSP role, a FOH gig and a transducer engineering job all get lumped into the
			same keyword soup — and great companies stay hidden because nobody indexes
			their careers page.
		</p>
		<p>
			So we're building the board ourselves. <strong class="font-semibold"
				>Young Audio Professionals (YAP)</strong
			>, a peer community of people working across studios, venues, labs and product
			teams, maintains {directoryPhrase}. Every night, our scraper re-reads each
			verified company's careers page so listings here reflect what's actually open —
			and when a job disappears from the source, it disappears here too.
			Community-submitted roles are reviewed by human moderators before they go live.
		</p>
		<p>
			No pay-to-post ranking, no recruiter gatekeeping, no cut of anything. Just the
			signal.
		</p>
	</div>

	<dl class="mt-16 grid gap-10 sm:grid-cols-3 sm:gap-6">
		<div class="flex flex-col">
			<dt class="axis-label order-2 mt-2">audio companies indexed</dt>
			<dd class="order-1 text-display font-light tracking-tight tabular-nums">
				{companyCount ?? '—'}
			</dd>
		</div>
		<div class="flex flex-col">
			<dt class="axis-label order-2 mt-2">specialty categories</dt>
			<dd class="order-1 text-display font-light tracking-tight tabular-nums">
				{categoryCount ?? '—'}
			</dd>
		</div>
		<div class="flex flex-col">
			<dt class="axis-label order-2 mt-2">free for seekers and posters</dt>
			<dd class="order-1 text-display font-light tracking-tight tabular-nums">100%</dd>
		</div>
	</dl>

	<section class="mt-20 border-t border-rule pt-10">
		<h2 class="text-title font-medium tracking-tight">Join Young Audio Professionals</h2>
		{#if discord}
			<p class="mt-3 max-w-[68ch] text-body leading-relaxed text-muted">
				The Discord is where this gets built: job leads, portfolio feedback,
				interview war stories and the occasional synth patch.
			</p>
			<a href={discord} target="_blank" rel="noopener noreferrer" class="btn btn-primary mt-6">
				Join the Discord<svg width="11" height="11" viewBox="0 0 16 16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M6 3h7v7M13 3L6.5 9.5M11 11v2H3V5h2"/></svg>
			</a>
		{:else}
			<p class="mt-3 max-w-[68ch] text-body leading-relaxed text-muted">
				Our Discord invite link is being rotated — check back shortly.
			</p>
		{/if}
	</section>

	<p class="mt-20 max-w-[68ch] text-body leading-relaxed text-muted">
		Questions or corrections? Find us in the YAP Discord, or submit fixes directly
		via any listing's source link.
	</p>
</div>
