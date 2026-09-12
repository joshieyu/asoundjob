<script lang="ts">
	import { page } from '$app/state';
	import discordLink from '$lib/data/discord-link.txt?raw';
	import { SITE_FEEDBACK_KINDS } from '$lib/feedback';
	import FeedbackDialog from './FeedbackDialog.svelte';

	const discord = discordLink.trim();
	const year = new Date().getFullYear();

	let feedbackOpen = $state(false);
	const pagePath = $derived(page.url.pathname);
</script>

<footer class="mt-auto border-t border-rule" aria-label="Site footer">
	<div class="mx-auto grid max-w-6xl gap-10 px-4 py-14 sm:grid-cols-2 sm:px-6 lg:grid-cols-4">
		<div>
			<h2 class="text-meta font-bold">ASoundJob</h2>
			<p class="mt-3 max-w-xs text-meta text-muted">
				The audio industry job board. Real listings from audio companies, filtered by
				specialties that matter. 
			</p>
		</div>
		<nav aria-labelledby="footer-find-work">
			<h2 id="footer-find-work" class="text-meta font-bold">Find work</h2>
			<ul class="mt-3 space-y-2 text-meta">
				<li><a class="text-muted hover:text-accent hover:underline" href="/jobs">Browse jobs</a></li>
				<li><a class="text-muted hover:text-accent hover:underline" href="/jobs?remote=true">Remote roles</a></li>
				<li><a class="text-muted hover:text-accent hover:underline" href="/jobs?seniority=entry">Entry level</a></li>
				<li><a class="text-muted hover:text-accent hover:underline" href="/jobs/submit">Submit a job</a></li>
			</ul>
		</nav>
		<nav aria-labelledby="footer-site">
			<h2 id="footer-site" class="text-meta font-bold">Site</h2>
			<ul class="mt-3 space-y-2 text-meta">
				<li><a class="text-muted hover:text-accent hover:underline" href="/companies">Company directory</a></li>
				<li><a class="text-muted hover:text-accent hover:underline" href="/resources/interview-prep">Interview prep</a></li>
				<li><a class="text-muted hover:text-accent hover:underline" href="/resources">Career resources</a></li>
				<li><a class="text-muted hover:text-accent hover:underline" href="/about">About</a></li>
			</ul>
		</nav>
		<div>
			<h2 class="text-meta font-bold">Community</h2>
			<p class="mt-3 text-meta text-muted">
				Built by <strong class="font-semibold text-ink">Young Audio Professionals</strong>, a
				peer community for people working in audio.
			</p>
			{#if discord}
				<a
					href={discord}
					target="_blank"
					rel="noopener noreferrer"
					class="btn btn-quiet mt-4"
				>
					Join the Discord<span class="sr-only"> (opens in a new tab)</span>
				</a>
			{/if}
		</div>
	</div>
	<div class="border-t border-rule">
		<div
			class="coord mx-auto flex max-w-6xl flex-col gap-2 px-4 py-4 text-muted sm:flex-row sm:items-center sm:justify-between sm:px-6"
		>
			<span>© {year} ASoundJob · Young Audio Professionals</span>
			<span class="flex flex-wrap items-center gap-4">
				<span>Listings refresh nightly · Community posts are reviewed before publishing</span>
				<button type="button" class="text-ink underline hover:text-accent" onclick={() => (feedbackOpen = true)}>
					Send feedback
				</button>
			</span>
		</div>
	</div>
</footer>

<FeedbackDialog mode="site" kinds={SITE_FEEDBACK_KINDS} {pagePath} bind:open={feedbackOpen} />
