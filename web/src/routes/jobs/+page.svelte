<script lang="ts">
	import { page } from '$app/state';
	import JobStrip from '$lib/components/JobStrip.svelte';
	import Pagination from '$lib/components/Pagination.svelte';
	import type { Paginated, Job } from '$lib/types';

	let { data } = $props();

	const jobs: Paginated<Job> | null = $derived(data.jobs);
	const params = $derived(data.params as Record<string, string>);

	function href(overrides: Record<string, string | undefined>): string {
		const next = new URLSearchParams(page.url.searchParams);
		for (const [key, value] of Object.entries(overrides)) {
			if (value === undefined || value === '') next.delete(key);
			else next.set(key, value);
		}
		next.delete('page');
		const qs = next.toString();
		return qs ? `/jobs?${qs}` : '/jobs';
	}

	const activeFilters = $derived.by(() => {
		const labels: { key: string; label: string; value: string }[] = [];
		if (params.q) labels.push({ key: 'q', label: 'Search', value: `“${params.q}”` });
		if (params.category)
			for (const c of params.category.split(','))
				labels.push({ key: 'category', label: 'Specialty', value: c });
		if (params.seniority)
			labels.push({ key: 'seniority', label: 'Level', value: params.seniority });
		if (params.job_type) labels.push({ key: 'job_type', label: 'Type', value: params.job_type });
		if (params.location)
			labels.push({ key: 'location', label: 'Near', value: params.location });
		if (params.remote) labels.push({ key: 'remote', label: '', value: 'Remote only' });
		if (params.salary_min)
			labels.push({ key: 'salary_min', label: 'Pays at least', value: `$${params.salary_min}` });
		if (params.company_id) {
			const name = data.companies?.items.find((c) => String(c.id) === params.company_id)?.name;
			labels.push({ key: 'company_id', label: 'Company', value: name ?? `#${params.company_id}` });
		}
		return labels;
	});

	function removeFilter(key: string, value?: string): Record<string, string | undefined> {
		if (key === 'category' && params.category?.includes(',')) {
			const rest = params.category
				.split(',')
				.filter((c) => c !== value)
				.join(',');
			return { category: rest };
		}
		const out: Record<string, string | undefined> = {};
		out[key] = undefined;
		return out;
	}

	const totalSegments = $derived(Math.round(((jobs?.total ?? 0) / 3200) * 16));

	function pageHref(p: number): string {
		const next = new URLSearchParams(page.url.searchParams);
		next.set('page', String(p));
		return `/jobs?${next.toString()}`;
	}
</script>

<svelte:head>
	<title>Audio industry jobs | ASoundJob</title>
	<meta
		name="description"
		content="Browse audio industry jobs — DSP, live sound, acoustics, game audio and more. Filter by specialty, level, salary and remote."
	/>
	<link rel="canonical" href="http://localhost:5173/jobs" />
</svelte:head>

<div class="mt-6 grid gap-6 lg:grid-cols-[17rem_1fr]">
	<form method="get" action="/jobs" class="panel h-fit p-4 lg:sticky lg:top-20" aria-label="Job filters">
		<h2 class="legend">FILTER RACK</h2>

		{#if params.q}
			<input type="hidden" name="q" value={params.q} />
		{/if}

		<fieldset class="mt-4">
			<legend class="mb-1.5 font-mono text-[10px] tracking-[0.14em] text-ink-soft uppercase">
				Specialty
			</legend>
			<select name="category" class="well h-9 w-full px-2 text-sm">
				<option value="">All specialties</option>
				{#each data.categories?.categories ?? [] as cat (cat.id)}
					<option value={cat.id} selected={params.category === cat.id}>
						{cat.name} ({cat.job_count})
					</option>
				{/each}
			</select>
		</fieldset>

		<fieldset class="mt-3">
			<legend class="mb-1.5 font-mono text-[10px] tracking-[0.14em] text-ink-soft uppercase">
				Level
			</legend>
			<select name="seniority" class="well h-9 w-full px-2 text-sm">
				<option value="">Any level</option>
				{#each ['entry', 'mid', 'senior', 'lead', 'manager'] as lvl (lvl)}
					<option value={lvl} selected={params.seniority === lvl}>{lvl}</option>
				{/each}
			</select>
		</fieldset>

		<fieldset class="mt-3">
			<legend class="mb-1.5 font-mono text-[10px] tracking-[0.14em] text-ink-soft uppercase">
				Type
			</legend>
			<select name="job_type" class="well h-9 w-full px-2 text-sm">
				<option value="">Any type</option>
				{#each ['full-time', 'part-time', 'contract', 'internship', 'temporary'] as t (t)}
					<option value={t} selected={params.job_type === t}>{t}</option>
				{/each}
			</select>
		</fieldset>

		<fieldset class="mt-3">
			<legend class="mb-1.5 font-mono text-[10px] tracking-[0.14em] text-ink-soft uppercase">
				Location contains
			</legend>
			<input
				name="location"
				value={params.location ?? ''}
				placeholder="e.g. Los Angeles"
				class="well h-9 w-full px-2 text-sm placeholder:text-ink-soft"
			/>
			<label class="mt-2 flex items-center gap-2 text-sm font-semibold">
				<input
					type="checkbox"
					name="remote"
					value="true"
					checked={params.remote === 'true'}
					class="h-4 w-4 accent-[#d96c2c]"
				/>
				Remote only
			</label>
		</fieldset>

		<fieldset class="mt-3">
			<legend class="mb-1.5 font-mono text-[10px] tracking-[0.14em] text-ink-soft uppercase">
				Annual salary (USD)
			</legend>
			<div class="flex items-center gap-2">
				<input
					type="number"
					name="salary_min"
					min="0"
					step="5000"
					value={params.salary_min ?? ''}
					placeholder="Min"
					aria-label="Minimum salary"
					class="well h-9 w-full px-2 font-mono text-sm placeholder:text-ink-soft"
				/>
				<span class="text-ink-soft">–</span>
				<input
					type="number"
					name="salary_max"
					min="0"
					step="5000"
					value={params.salary_max ?? ''}
					placeholder="Max"
					aria-label="Maximum salary"
					class="well h-9 w-full px-2 font-mono text-sm placeholder:text-ink-soft"
				/>
			</div>
		</fieldset>

		<fieldset class="mt-3">
			<legend class="mb-1.5 font-mono text-[10px] tracking-[0.14em] text-ink-soft uppercase">
				Company
			</legend>
			<select name="company_id" class="well h-9 w-full px-2 text-sm">
				<option value="">All companies</option>
				{#each data.companies?.items ?? [] as company (company.id)}
					<option value={company.id} selected={params.company_id === String(company.id)}>
						{company.name}
					</option>
				{/each}
			</select>
		</fieldset>

		<fieldset class="mt-3">
			<legend class="mb-1.5 font-mono text-[10px] tracking-[0.14em] text-ink-soft uppercase">
				Sort
			</legend>
			<select name="sort" class="well h-9 w-full px-2 text-sm">
				{#each [['newest', 'Newest first'], ['oldest', 'Oldest first'], ['salary_desc', 'Salary high → low'], ['salary_asc', 'Salary low → high']] as [value, labelText] (value)}
					<option value={value} selected={(params.sort ?? 'newest') === value}>{labelText}</option>
				{/each}
			</select>
		</fieldset>

		<div class="mt-4 flex items-center gap-2">
			<button type="submit" class="btn-primary flex-1">Apply</button>
			<a href="/jobs" class="btn-latch">Reset</a>
		</div>
	</form>

	<section aria-label="Job results">
		<div class="flex flex-wrap items-center justify-between gap-3">
			<p class="flex items-center gap-3">
				<span class="meter-sweep flex h-4 items-stretch gap-[2px]" aria-hidden="true">
					{#each Array.from({ length: 16 }, (_, i) => i) as seg (seg)}
						<span
							class="w-1.5 rounded-[1px] {seg < totalSegments ? 'bg-lit' : 'bg-led-0'}"
						></span>
					{/each}
				</span>
				<span class="readout text-sm text-ink-soft">
					<span class="text-xl font-semibold text-ink">
						{(jobs?.total ?? 0).toLocaleString('en-US')}
					</span>
					open roles
				</span>
			</p>
			<a href="/jobs/submit" class="font-mono text-xs font-semibold tracking-wide hover:text-fader-deep">
				Know a missing role? Submit it →
			</a>
		</div>

		{#if activeFilters.length > 0}
			<ul class="mt-3 flex flex-wrap items-center gap-1.5" aria-label="Active filters">
				{#each activeFilters as f (f.key + f.value)}
					<li>
						<a
							href={href(removeFilter(f.key, f.value))}
							class="btn-latch !normal-case !tracking-normal is-on !py-1 !text-xs"
						>
							{#if f.label}<span class="opacity-70">{f.label}:</span>{/if}
							{f.value} ✕
						</a>
					</li>
				{/each}
			</ul>
		{/if}

		<div class="mt-4 grid gap-3 xl:grid-cols-2">
			{#each jobs?.items ?? [] as job (job.id)}
				<JobStrip {job} />
			{:else}
				<div class="panel col-span-full p-8 text-center">
					<p class="font-mono text-sm text-ink-soft">
						NO SIGNAL — no roles match this filter setting.
					</p>
					<a href="/jobs" class="btn-latch mt-4">Reset the rack</a>
				</div>
			{/each}
		</div>

		{#if jobs}
			<Pagination data={jobs} makeHref={pageHref} />
		{/if}
	</section>
</div>
