<script lang="ts">
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	const blocked = $derived(data.blocked);
</script>

<svelte:head>
	<title>Companies we can't scrape | ASoundJob</title>
	<meta
		name="description"
		content="Audio companies whose careers pages block automated readers — their roles never reach this board, so it's worth checking them directly."
	/>
	<link rel="canonical" href="http://localhost:5173/companies/blocked" />
</svelte:head>

<div class="mx-auto mt-8 max-w-3xl">
	<p class="legend">CAN'T SCRAPE</p>
	<h1 class="mt-3 text-4xl font-black tracking-tight text-balance sm:text-5xl">
		Companies our scraper can't read.
	</h1>

	<div class="panel mt-6 p-6 sm:p-8">
		<p class="text-[15px] leading-relaxed">
			Some careers pages are built to keep automated readers out — a Cloudflare challenge, a
			captcha, a flat 403. Our scraper hits the wall and stops, so any roles open at these
			companies never make it onto this board.
		</p>
		<p class="mt-4 text-[15px] leading-relaxed">
			We're not saying any of them are hiring right now — we just can't tell either way. These
			are real audio companies we know exist. If one of them is a fit, go look at their careers
			page directly.
		</p>
	</div>

	<div class="well mt-6 p-6 sm:p-8">
		<p class="font-mono text-[10px] tracking-[0.14em] text-ink-soft uppercase">One more thing</p>
		<p class="mt-2 text-[15px] leading-relaxed">
			Searching <strong>"acoustic engineer"</strong> on LinkedIn surfaces a lot of roles that never
			make it onto a company's own careers page, blocked or not.
		</p>
		<a
			href="https://www.linkedin.com/jobs/search/?keywords=acoustic%20engineer"
			target="_blank"
			rel="noopener noreferrer"
			class="btn-latch mt-4"
		>
			Search LinkedIn ↗
		</a>
	</div>

	<section class="mt-10" aria-labelledby="blocked-companies-heading">
		<div class="flex items-center gap-3">
			<span class="h-px flex-1 bg-ink-soft/25"></span>
			<span class="font-mono text-[10px] tracking-[0.14em] text-ink-soft uppercase">
				Blocked companies
			</span>
			<span class="h-px flex-1 bg-ink-soft/25"></span>
		</div>

		{#if blocked && blocked.total > 0}
			<h2 id="blocked-companies-heading" class="mt-3 text-sm font-bold">
				{blocked.total} companies we can't read
			</h2>
			<ul class="mt-4 grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
				{#each blocked.companies as company (company.id)}
					<li class="well flex items-center justify-between gap-3 p-3">
						<span class="min-w-0">
							<span class="block truncate text-sm font-semibold">{company.name}</span>
							<span class="block truncate font-mono text-[10px] tracking-wide text-ink-soft uppercase">
								{company.category}
							</span>
						</span>
						{#if company.careers_url}
							<a
								href={company.careers_url}
								target="_blank"
								rel="noopener noreferrer"
								class="btn-latch shrink-0 !px-2 !py-1 text-xs"
							>
								Careers
							</a>
						{/if}
					</li>
				{/each}
			</ul>
		{:else}
			<p class="mt-4 text-sm text-ink-soft">
				Nothing is currently on this list — every company we track is readable right now.
			</p>
		{/if}
	</section>
</div>
