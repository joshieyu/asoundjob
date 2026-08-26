<script lang="ts">
	import discordLink from '$lib/data/discord-link.txt?raw';

	const discord = discordLink.trim();
	const year = new Date().getFullYear();
</script>

<footer class="mt-auto border-t border-seam bg-panel">
	<div class="mx-auto grid max-w-6xl gap-8 px-4 py-10 sm:grid-cols-2 sm:px-6 lg:grid-cols-4">
		<div>
			<p class="legend">ASoundJob</p>
			<p class="mt-3 max-w-xs text-sm text-ink-soft">
				The audio industry job board. Real listings from real audio companies,
				filtered by the specialties we actually work in.
			</p>
		</div>
		<div>
			<p class="legend">Find work</p>
			<ul class="mt-3 space-y-2 text-sm font-semibold">
				<li><a class="hover:text-fader-deep hover:underline" href="/jobs">Browse jobs</a></li>
				<li><a class="hover:text-fader-deep hover:underline" href="/jobs?remote=true">Remote roles</a></li>
				<li><a class="hover:text-fader-deep hover:underline" href="/jobs?seniority=entry">Entry level</a></li>
				<li><a class="hover:text-fader-deep hover:underline" href="/jobs/submit">Submit a job</a></li>
			</ul>
		</div>
		<div>
			<p class="legend">Site</p>
			<ul class="mt-3 space-y-2 text-sm font-semibold">
				<li><a class="hover:text-fader-deep hover:underline" href="/companies">Company directory</a></li>
				<li><a class="hover:text-fader-deep hover:underline" href="/resources/interview-prep">Interview prep</a></li>
				<li><a class="hover:text-fader-deep hover:underline" href="/resources">Career resources</a></li>
				<li><a class="hover:text-fader-deep hover:underline" href="/about">About</a></li>
			</ul>
		</div>
		<div>
			<p class="legend">Community</p>
			<p class="mt-3 text-sm text-ink-soft">
				Built by <strong class="text-ink">Young Audio Professionals</strong>, a peer community
				for people working in audio.
			</p>
			{#if discord}
				<a href={discord} target="_blank" rel="noopener noreferrer" class="btn-latch mt-3 is-on">
					Join the Discord ↗
				</a>
			{/if}
		</div>
	</div>
	<div class="border-t border-seam">
		<div
			class="mx-auto flex max-w-6xl flex-col gap-1 px-4 py-3 font-mono text-[11px] tracking-wide text-ink-soft sm:flex-row sm:items-center sm:justify-between sm:px-6"
		>
			<span>© {year} ASoundJob · Young Audio Professionals</span>
			<span>Listings refresh nightly · Community posts are reviewed before publishing</span>
		</div>
	</div>
</footer>
