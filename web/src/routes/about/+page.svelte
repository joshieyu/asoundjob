<script lang="ts">
	import discordLink from '$lib/data/discord-link.txt?raw';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	const discord = discordLink.trim();
	const companyCount = $derived(data.companyCount.toLocaleString('en-US'));
	const categoryCount = $derived(data.categoryCount);
</script>

<svelte:head>
	<title>About | ASoundJob</title>
	<meta
		name="description"
		content="ASoundJob is built by Young Audio Professionals — a peer community for people working in audio."
	/>
	<link rel="canonical" href="http://localhost:5173/about" />
</svelte:head>

<div class="mx-auto mt-8 max-w-3xl">
	<p class="legend">ABOUT</p>
	<h1 class="mt-3 text-4xl font-black tracking-tight text-balance sm:text-5xl">
		Built by the community that works in audio.
	</h1>

	<div class="panel mt-6 p-6 sm:p-8">
		<p class="text-[15px] leading-relaxed">
			ASoundJob exists because audio careers are invisible on generic job boards. A
			DSP role, a FOH gig and a transducer engineering job all get lumped into the
			same keyword soup — and great companies stay hidden because nobody indexes
			their careers page.
		</p>
		<p class="mt-4 text-[15px] leading-relaxed">
			So we're building the board ourselves. <strong>Young Audio Professionals (YAP)</strong>,
			a peer community of people working across studios, venues, labs and product
			teams, maintains a directory of 1,385 audio companies. Every night, our scraper
			re-reads each verified company's careers page so listings here reflect what's
			actually open — and when a job disappears from the source, it disappears here
			too. Community-submitted roles are reviewed by human moderators before they go
			live.
		</p>
		<p class="mt-4 text-[15px] leading-relaxed">
			No pay-to-post ranking, no recruiter gatekeeping, no cut of anything. Just the
			signal.
		</p>
	</div>

	<div class="mt-6 grid gap-3 sm:grid-cols-3">
		<div class="well p-4">
			<p class="font-mono text-xl font-semibold">{companyCount}</p>
			<p class="mt-0.5 text-sm text-ink-soft">audio companies indexed</p>
		</div>
		<div class="well p-4">
			<p class="font-mono text-xl font-semibold">{categoryCount}</p>
			<p class="mt-0.5 text-sm text-ink-soft">specialty categories</p>
		</div>
		<div class="well p-4">
			<p class="font-mono text-xl font-semibold">100%</p>
			<p class="mt-0.5 text-sm text-ink-soft">free for seekers and posters</p>
		</div>
	</div>

	{#if discord}
		<section class="panel mt-6 flex flex-col items-start justify-between gap-4 p-6 sm:flex-row sm:items-center">
			<div>
				<h2 class="text-lg font-bold tracking-tight">Join Young Audio Professionals</h2>
				<p class="mt-1 max-w-md text-sm text-ink-soft">
					The Discord is where this gets built: job leads, portfolio feedback,
					interview war stories and the occasional synth patch.
				</p>
			</div>
			<a href={discord} target="_blank" rel="noopener noreferrer" class="btn-primary shrink-0">
				Join the Discord ↗
			</a>
		</section>
	{:else}
		<section class="panel mt-6 p-6">
			<h2 class="text-lg font-bold tracking-tight">Join Young Audio Professionals</h2>
			<p class="mt-1 max-w-md text-sm text-ink-soft">
				Our Discord invite link is being rotated — check back shortly.
			</p>
		</section>
	{/if}

	<p class="mt-8 font-mono text-xs tracking-wide text-ink-soft">
		Questions or corrections? Find us in the YAP Discord, or submit fixes directly
		via any listing's source link.
	</p>
</div>
