<script lang="ts">
	import JobStrip from '$lib/components/JobStrip.svelte';
	import jobCategories from '$lib/data/job-categories.json';

	let { data } = $props();

	const total = $derived(data.totalJobs);
	const featured = $derived(data.featured?.items ?? []);
	const counts = $derived.by(() => {
		const map = new Map<string, number>();
		for (const c of data.categories?.categories ?? []) map.set(c.id, c.job_count);
		return map;
	});
	const categoryMeta = jobCategories.job_categories;
	const topCategories = $derived(
		[...categoryMeta]
			.map((c) => ({ ...c, count: counts.get(c.id) ?? 0 }))
			.sort((a, b) => b.count - a.count)
	);
	const maxCount = $derived(topCategories[0]?.count ?? 1);
</script>

<svelte:head>
	<title>{data.meta.title}</title>
	<meta name="description" content={data.meta.description} />
	<link rel="canonical" href="http://localhost:5173/" />
</svelte:head>

<section
	class="panel mt-4 overflow-hidden"
	aria-labelledby="hero-heading"
>
	<div class="border-b border-seam bg-panel-recessed px-4 py-2 sm:px-6">
		<h1 id="hero-heading" class="legend !text-ink">MASTER SECTION — AUDIO JOBS</h1>
	</div>

	<div class="grid gap-6 p-4 sm:p-6 lg:grid-cols-[auto_1fr]">
		<div class="well flex flex-col justify-between rounded-md bg-ink px-6 py-5 text-panel sm:min-w-[16rem]">
			<p class="font-mono text-[11px] tracking-[0.14em] text-panel/60 uppercase">Open roles</p>
			<p
				class="readout readout-power mt-2 text-6xl leading-none font-semibold text-lit sm:text-7xl"
				style="text-shadow: 0 0 12px rgb(47 143 87 / 0.45)"
			>
				{total.toLocaleString('en-US')}
			</p>
			<p class="mt-3 font-mono text-[11px] tracking-wide text-panel/60">
				refreshed nightly from verified audio companies
			</p>
		</div>

		<div class="flex flex-col gap-4">
			<form action="/jobs" method="get" role="search" class="flex flex-col gap-2 sm:flex-row">
				<label class="sr-only" for="q">Search jobs</label>
				<input
					id="q"
					name="q"
					type="search"
					placeholder="Search titles, skills, companies…"
					class="well h-11 w-full px-3.5 text-sm outline-none placeholder:text-ink-soft"
				/>
				<button type="submit" class="btn-primary h-11 shrink-0">Find jobs</button>
			</form>

			<div>
				<p class="mb-2 font-mono text-[11px] tracking-[0.14em] text-ink-soft uppercase">
					Filter by specialty
				</p>
				<ul class="flex flex-wrap gap-1.5">
					{#each topCategories.slice(0, 10) as cat (cat.id)}
						<li>
							<a
								href="/jobs?category={cat.id}"
								class="btn-latch !normal-case !tracking-normal"
								title="{cat.name} — {cat.count} open roles"
							>
								{cat.name}
								<span
									class="rounded-sm border border-seam bg-panel-recessed px-1 font-mono text-[10px] {''}"
									>{cat.count}</span
								>
							</a>
						</li>
					{/each}
					<li>
						<a href="/jobs" class="btn-latch is-on !normal-case !tracking-normal">All jobs →</a>
					</li>
				</ul>
			</div>
		</div>
	</div>

	<div class="flex items-center gap-3 border-t border-seam bg-panel px-4 py-2 sm:px-6">
		<span class="font-mono text-[11px] tracking-[0.14em] text-ink-soft uppercase">Signal</span>
		{#each topCategories.slice(0, 8) as cat (cat.id)}
			<span
				class="h-2 flex-1 rounded-sm bg-led-0"
				style="background: linear-gradient(to right, var(--color-fader) {(cat.count /
					maxCount) * 100}%, var(--color-led-0) {(cat.count / maxCount) * 100}%)"
				title="{cat.name}: {cat.count}"
			></span>
		{/each}
		<span class="hidden font-mono text-[10px] tracking-wide text-ink-soft sm:inline">
			jobs by specialty
		</span>
	</div>
</section>

<section class="mt-10" aria-labelledby="featured-heading">
	<div class="flex items-end justify-between gap-4">
		<h2 id="featured-heading" class="legend !text-sm">FRESH ON THE BOARD</h2>
		<a href="/jobs" class="font-mono text-xs font-semibold tracking-wide hover:text-fader-deep">
			Browse all {total.toLocaleString('en-US')} →
		</a>
	</div>

	<div class="mt-4 grid gap-3 md:grid-cols-2">
		{#each featured as job (job.id)}
			<JobStrip {job} />
		{:else}
			<p class="panel col-span-full p-6 text-sm text-ink-soft">
				Listings are warming up — the board is syncing with the backend.
			</p>
		{/each}
	</div>
</section>

<section class="mt-12 grid gap-3 sm:grid-cols-3" aria-label="Why ASoundJob">
	<div class="panel p-5">
		<p class="font-mono text-2xl font-semibold">{total ? 'NIGHTLY' : '—'}</p>
		<h3 class="mt-1 text-sm font-bold tracking-wide uppercase">Refreshed, not stale</h3>
		<p class="mt-1.5 text-sm text-ink-soft">
			A scraper re-checks every verified company's careers page each night. When a
			job disappears from the source, it disappears here.
		</p>
	</div>
	<div class="panel p-5">
		<p class="font-mono text-2xl font-semibold">{categoryMeta.length}</p>
		<h3 class="mt-1 text-sm font-bold tracking-wide uppercase">Audio specialties</h3>
		<p class="mt-1.5 text-sm text-ink-soft">
			DSP, live sound, acoustics, transducers, game audio — filter by the work you
			actually do, not keyword soup.
		</p>
	</div>
	<div class="panel p-5">
		<p class="font-mono text-2xl font-semibold">30 DAYS</p>
		<h3 class="mt-1 text-sm font-bold tracking-wide uppercase">Community reviewed</h3>
		<p class="mt-1.5 text-sm text-ink-soft">
			Every community submission is approved by a human moderator before it goes
			live, and expires after a month.
		</p>
	</div>
</section>

<section class="panel mt-12 flex flex-col items-start justify-between gap-4 p-6 sm:flex-row sm:items-center">
	<div>
		<h2 class="text-lg font-bold tracking-tight">Hiring in audio?</h2>
		<p class="mt-1 max-w-lg text-sm text-ink-soft">
			Put your opening in front of the people who speak this language. Submissions
			are free and reviewed by the Young Audio Professionals community within days.
		</p>
	</div>
	<a href="/jobs/submit" class="btn-primary shrink-0">Submit a job</a>
</section>
