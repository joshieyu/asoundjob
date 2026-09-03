<script lang="ts">
	import { page } from '$app/state';
	import JobStrip from '$lib/components/JobStrip.svelte';
	import Pagination from '$lib/components/Pagination.svelte';
	import FeedbackDialog from '$lib/components/FeedbackDialog.svelte';
	import { JOB_FEEDBACK_KINDS } from '$lib/feedback';
	import { getBookmarks } from '$lib/client';
	import type { Paginated, Job } from '$lib/types';

	let { data } = $props();

	const jobs: Paginated<Job> | null = $derived(data.jobs);
	const params = $derived(data.params as Record<string, string>);

	const categoryNames = $derived.by(() => {
		const map = new Map<string, string>();
		for (const c of data.categories?.categories ?? []) map.set(c.id, c.name);
		return map;
	});

	const categoryOptions = $derived(
		(data.categories?.categories ?? []).map((c) => ({ id: c.id, name: c.name }))
	);

	const reportKinds = JOB_FEEDBACK_KINDS.filter(
		(k) => k.value === 'wrong_category' || k.value === 'not_audio'
	);

	let reportJob = $state<Job | null>(null);
	let reportOpen = $state(false);

	let bookmarkedOnly = $state(false);
	let bookmarkIds = $state<number[]>([]);

	$effect(() => {
		bookmarkedOnly = data.bookmarked;
	});

	$effect(() => {
		bookmarkIds = [...getBookmarks()];
	});

	const bookmarkFieldValue = $derived(bookmarkIds.join(',') || '0');

	function onReport(job: Job) {
		reportJob = job;
		reportOpen = true;
	}

	let selectedCategories = $state<string[]>(params.category ? params.category.split(',') : []);
	let showZeroCategories = $state(false);

	$effect(() => {
		selectedCategories = params.category ? params.category.split(',') : [];
	});

	function toggleCategory(id: string, checked: boolean) {
		if (checked) {
			if (!selectedCategories.includes(id)) selectedCategories = [...selectedCategories, id];
		} else {
			selectedCategories = selectedCategories.filter((c) => c !== id);
		}
	}

	const categoryFieldValue = $derived(selectedCategories.join(','));

	const countryOptions = $derived(data.countries?.countries ?? []);
	const unknownCountryCount = $derived(data.countries?.unknown_count ?? 0);
	const unplacedStartIndex = $derived.by(() => {
		if (!params.country) return -1;
		return data.jobs?.items.findIndex((job) => job.country === null) ?? -1;
	});
	const selectedCountryName = $derived(
		countryOptions.find((c) => c.code === params.country)?.name ?? params.country ?? ''
	);

	const unselectedZeroCategories = $derived(
		(data.categories?.categories ?? []).filter(
			(c) => c.job_count === 0 && !selectedCategories.includes(c.id)
		)
	);

	const visibleCategories = $derived(
		(data.categories?.categories ?? []).filter(
			(c) => c.job_count > 0 || showZeroCategories || selectedCategories.includes(c.id)
		)
	);

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
		const labels: { key: string; label: string; value: string; id?: string }[] = [];
		if (params.q) labels.push({ key: 'q', label: 'Search', value: `“${params.q}”` });
		if (params.category)
			for (const c of params.category.split(','))
				labels.push({
					key: 'category',
					label: 'Specialty',
					value: categoryNames.get(c) ?? c,
					id: c
				});
		if (params.seniority)
			labels.push({ key: 'seniority', label: 'Level', value: params.seniority });
		if (params.job_type) labels.push({ key: 'job_type', label: 'Type', value: params.job_type });
		if (params.country)
			labels.push({ key: 'country', label: 'Country', value: selectedCountryName });
		if (params.location)
			labels.push({ key: 'location', label: 'Near', value: params.location });
		if (params.remote) labels.push({ key: 'remote', label: '', value: 'Remote only' });
		if (params.include_unrelated)
			labels.push({ key: 'include_unrelated', label: '', value: 'Including non-audio roles' });
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

	const boardTotal = $derived(data.totalJobs || 1);
	const totalSegments = $derived(
		Math.min(16, Math.max(0, Math.round(((jobs?.total ?? 0) / boardTotal) * 16)))
	);

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
			<input type="hidden" name="category" value={categoryFieldValue} />
			<div class="well max-h-64 overflow-y-auto p-1.5">
				{#each visibleCategories as cat (cat.id)}
					<label class="flex items-center gap-2 rounded-sm px-1.5 py-1 text-sm hover:bg-panel-recessed">
						<input
							type="checkbox"
							checked={selectedCategories.includes(cat.id)}
							onchange={(e) => toggleCategory(cat.id, e.currentTarget.checked)}
							class="h-4 w-4 shrink-0 accent-fader"
						/>
						<span class="min-w-0 flex-1 truncate">{cat.name}</span>
						<span class="shrink-0 font-mono text-[10px] text-ink-soft">({cat.job_count})</span>
					</label>
				{/each}
				{#if unselectedZeroCategories.length > 0}
					<button
						type="button"
						class="mt-1 w-full rounded-sm px-1.5 py-1 text-left font-mono text-[10px] tracking-wide text-ink-soft hover:text-fader-deep"
						onclick={() => (showZeroCategories = !showZeroCategories)}
					>
						{showZeroCategories
							? 'Hide specialties with no open roles'
							: `Show ${unselectedZeroCategories.length} specialties with no open roles`}
					</button>
				{/if}
			</div>
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
				Country
			</legend>
			<select name="country" class="well h-9 w-full px-2 text-sm">
				<option value="">Anywhere</option>
				{#each countryOptions as c (c.code)}
					<option value={c.code} selected={params.country === c.code}>
						{c.name} ({c.job_count})
					</option>
				{/each}
			</select>
			{#if params.country && unknownCountryCount > 0}
				<p class="mt-1.5 text-xs text-ink-soft">
					Matching roles come first, then {unknownCountryCount} whose location we could not
					place — so nothing in {selectedCountryName} is hidden.
				</p>
			{/if}
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
					class="h-4 w-4 accent-fader"
				/>
				Remote only
			</label>
			<label class="mt-1.5 flex items-center gap-2 text-sm font-semibold">
				<input
					type="checkbox"
					name="bookmarked"
					value="true"
					bind:checked={bookmarkedOnly}
					class="h-4 w-4 accent-fader"
				/>
				Bookmarked only
				<span class="font-mono text-[11px] font-normal text-ink-soft">
					({bookmarkIds.length})
				</span>
			</label>
			{#if bookmarkedOnly}
				<input type="hidden" name="ids" value={bookmarkFieldValue} />
			{/if}
			<label class="mt-1.5 flex items-start gap-2 text-sm font-semibold">
				<input
					type="checkbox"
					name="include_unrelated"
					value="true"
					checked={params.include_unrelated === 'true'}
					class="mt-0.5 h-4 w-4 accent-[#d96c2c]"
				/>
				<span>
					Include non-audio roles
					<span class="block text-xs font-normal text-ink-soft">
						Show every role at audio companies, not just audio-related ones
					</span>
				</span>
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
							href={href(removeFilter(f.key, f.id ?? f.value))}
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
			{#each jobs?.items ?? [] as job, i (job.id)}
				{#if i === unplacedStartIndex}
					<div class="col-span-full mt-2 flex items-center gap-3">
						<span class="h-px flex-1 bg-ink-soft/25"></span>
						<span class="font-mono text-[10px] tracking-[0.14em] text-ink-soft uppercase">
							Location not parsed — may still be in {selectedCountryName}
						</span>
						<span class="h-px flex-1 bg-ink-soft/25"></span>
					</div>
				{/if}
				<JobStrip {job} {categoryNames} {onReport} />
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
