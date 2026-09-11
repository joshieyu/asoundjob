<script lang="ts">
	import { page } from '$app/state';
	import JobStrip from '$lib/components/JobStrip.svelte';
	import Pagination from '$lib/components/Pagination.svelte';
	import FeedbackDialog from '$lib/components/FeedbackDialog.svelte';
	import Accordion from '$lib/components/Accordion.svelte';
	import { JOB_FEEDBACK_KINDS } from '$lib/feedback';
	import { bookmarks, hydrateBookmarks } from '$lib/bookmarks.svelte';
	import type { Paginated, Job } from '$lib/types';

	let { data } = $props();

	const jobs: Paginated<Job> | null = $derived(data.jobs);
	const openApplications = $derived(data.openApplications);
	const blocked = $derived(data.blocked);
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
	$effect(() => {
		bookmarkedOnly = data.bookmarked;
	});

	$effect(() => {
		hydrateBookmarks();
	});

	const bookmarkIds = $derived([...bookmarks.ids]);
	const bookmarkFieldValue = $derived(bookmarkIds.join(',') || '0');

	function onReport(job: Job) {
		reportJob = job;
		reportOpen = true;
	}

	let selectedCategories = $state<string[]>(params.category ? params.category.split(',') : []);
	let showZeroCategories = $state(false);

	const LEVELS = ['', 'entry', 'mid', 'senior', 'lead', 'manager'];
	let levelIndex = $state(0);
	let salaryFloor = $state(0);

	$effect(() => {
		levelIndex = Math.max(0, LEVELS.indexOf(data.params.seniority ?? ''));
	});
	$effect(() => {
		salaryFloor = Number(data.params.salary_min ?? 0) || 0;
	});

	const levelValue = $derived(LEVELS[levelIndex] ?? '');
	const coordinates = $derived.by(() => {
		const parts: string[] = [`${(jobs?.total ?? 0).toLocaleString('en-US')} open`];
		parts.push(
			selectedCategories.length > 0
				? `cat ${selectedCategories.length}/${categoryOptions.length}`
				: `cat all/${categoryOptions.length}`
		);
		parts.push(levelValue ? `lvl ${levelValue}` : 'lvl any');
		parts.push(salaryFloor > 0 ? `sal ${Math.round(salaryFloor / 1000)}k+` : 'sal any');
		if (params.country) parts.push(`country ${params.country}`);
		if (params.remote) parts.push('remote');
		if (bookmarkedOnly) parts.push('saved');
		parts.push(`sort ${params.sort ?? 'newest'}`);
		if ((jobs?.pages ?? 1) > 1) parts.push(`p${data.page}/${jobs?.pages ?? 1}`);
		return parts.join(' · ');
	});

	const salaryLabel = $derived(
		salaryFloor > 0 ? `${Math.round(salaryFloor / 1000)}k and up` : 'any salary'
	);

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
	<link rel="canonical" href="{data.siteUrl}/jobs" />
</svelte:head>

<h1 class="sr-only">Audio industry jobs</h1>

<div class="mt-6 grid gap-6 lg:grid-cols-[17rem_1fr]">
	<form method="get" action="/jobs" class="h-fit lg:sticky lg:top-24" aria-label="Job filters">
		<h2 class="text-title font-semibold">Filters</h2>

		{#if params.q}
			<input type="hidden" name="q" value={params.q} />
		{/if}

		<fieldset class="mt-4">
			<legend class="axis-label mb-2">
				Specialty
			</legend>
			<input type="hidden" name="category" value={categoryFieldValue} />
			<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
			<div class="max-h-72 overflow-y-auto border-y border-rule py-1" tabindex="0" role="region" aria-label="Specialty options">
				{#each visibleCategories as cat (cat.id)}
					<label class="flex items-center gap-2.5 py-1.5 text-meta hover:text-accent">
						<input
							type="checkbox"
							checked={selectedCategories.includes(cat.id)}
							onchange={(e) => toggleCategory(cat.id, e.currentTarget.checked)}
							class="h-4 w-4 shrink-0 accent-accent"
						/>
						<span class="min-w-0 flex-1 truncate">{cat.name}</span>
						<span class="coord shrink-0 text-muted">{cat.job_count}</span>
					</label>
				{/each}
				{#if unselectedZeroCategories.length > 0}
					<button
						type="button"
						class="coord mt-2 w-full text-left text-muted underline hover:text-accent"
						aria-expanded={showZeroCategories}
						onclick={() => (showZeroCategories = !showZeroCategories)}
					>
						{showZeroCategories
							? 'Hide specialties with no open roles'
							: `Show ${unselectedZeroCategories.length} specialties with no open roles`}
					</button>
				{/if}
			</div>
		</fieldset>

		<fieldset class="mt-6">
			<legend class="axis-label mb-2">Level</legend>
			<input type="hidden" name="seniority" value={levelValue} />
			<label class="sr-only" for="level-axis">Level</label>
			<input
				id="level-axis"
				type="range"
				min="0"
				max="5"
				step="1"
				bind:value={levelIndex}
				class="axis"
				aria-valuetext={levelValue || 'any level'}
			/>
			<p class="coord mt-1.5" aria-live="polite">{levelValue || 'any level'}</p>
			<noscript>
				<select name="seniority" class="field mt-2">
					<option value="">Any level</option>
					{#each ['entry', 'mid', 'senior', 'lead', 'manager'] as lvl (lvl)}
						<option value={lvl} selected={params.seniority === lvl}>{lvl}</option>
					{/each}
				</select>
			</noscript>
		</fieldset>

		<fieldset class="mt-3">
			<legend class="axis-label mb-2">
				Type
			</legend>
			<select name="job_type" class="field">
				<option value="">Any type</option>
				{#each ['full-time', 'part-time', 'contract', 'internship', 'temporary'] as t (t)}
					<option value={t} selected={params.job_type === t}>{t}</option>
				{/each}
			</select>
		</fieldset>

		<fieldset class="mt-3">
			<legend class="axis-label mb-2">
				Country
			</legend>
			<select name="country" class="field">
				<option value="">Anywhere</option>
				{#each countryOptions as c (c.code)}
					<option value={c.code} selected={params.country === c.code}>
						{c.name} ({c.job_count})
					</option>
				{/each}
			</select>
			{#if params.country && unknownCountryCount > 0}
				<p class="mt-1.5 text-coord text-muted">
					Matching roles come first, then {unknownCountryCount} whose location we could not
					place — so nothing in {selectedCountryName} is hidden.
				</p>
			{/if}
		</fieldset>

		<fieldset class="mt-3">
			<legend class="axis-label mb-2">
				Location contains
			</legend>
			<input
				name="location"
				value={params.location ?? ''}
				placeholder="e.g. Los Angeles"
				class="field"
			/>
			<label class="mt-2 flex items-center gap-2 text-meta font-semibold">
				<input
					type="checkbox"
					name="remote"
					value="true"
					checked={params.remote === 'true'}
					class="h-4 w-4 accent-accent"
				/>
				Remote only
			</label>
			<label class="mt-1.5 flex items-center gap-2 text-meta font-semibold">
				<input
					type="checkbox"
					name="bookmarked"
					value="true"
					bind:checked={bookmarkedOnly}
					class="h-4 w-4 accent-accent"
				/>
				Bookmarked only
				<span class="coord font-normal text-muted">
					({bookmarkIds.length})
				</span>
			</label>
			{#if bookmarkedOnly}
				<input type="hidden" name="ids" value={bookmarkFieldValue} />
			{/if}
			<label class="mt-1.5 flex items-start gap-2 text-meta font-semibold">
				<input
					type="checkbox"
					name="include_unrelated"
					value="true"
					checked={params.include_unrelated === 'true'}
					class="mt-0.5 h-4 w-4 accent-accent"
				/>
				<span>
					Include non-audio roles
					<span class="block text-coord font-normal text-muted">
						Show every role at audio companies, not just audio-related ones
					</span>
				</span>
			</label>
		</fieldset>

		<fieldset class="mt-3">
			<legend class="axis-label mb-2">
				Annual salary (USD)
			</legend>
			<label class="sr-only" for="salary-axis">Minimum salary</label>
			<input
				id="salary-axis"
				type="range"
				name="salary_min"
				min="0"
				max="300000"
				step="10000"
				bind:value={salaryFloor}
				class="axis"
				aria-valuetext={salaryLabel}
			/>
			<p class="coord mt-1.5 mb-3" aria-live="polite">{salaryLabel}</p>
			<div class="flex items-center gap-2">
				<label class="axis-label shrink-0" for="salary-max">Ceiling</label>
				<input
					id="salary-max"
					type="number"
					name="salary_max"
					min="0"
					step="5000"
					value={params.salary_max ?? ''}
					placeholder="Max"
					class="field"
				/>
			</div>
		</fieldset>

		<fieldset class="mt-3">
			<legend class="axis-label mb-2">
				Company
			</legend>
			<select name="company_id" class="field">
				<option value="">All companies</option>
				{#each data.companies?.items ?? [] as company (company.id)}
					<option value={company.id} selected={params.company_id === String(company.id)}>
						{company.name}
					</option>
				{/each}
			</select>
		</fieldset>

		<fieldset class="mt-3">
			<legend class="axis-label mb-2">
				Sort
			</legend>
			<select name="sort" class="field">
				{#each [['newest', 'Newest first'], ['oldest', 'Oldest first'], ['salary_desc', 'Salary, high to low'], ['salary_asc', 'Salary, low to high']] as [value, labelText] (value)}
					<option value={value} selected={(params.sort ?? 'newest') === value}>{labelText}</option>
				{/each}
			</select>
		</fieldset>

		<div class="mt-4 flex items-center gap-2">
			<button type="submit" class="btn btn-primary flex-1">Apply</button>
			<a href="/jobs" class="btn btn-quiet">Reset</a>
		</div>
	</form>

	<section aria-label="Job results">
		<p
			class="coord sticky top-16 z-30 -mx-1 mb-4 truncate border-b border-muted bg-ground/95 px-1 py-2 backdrop-blur"
			aria-live="polite"
			aria-label="Current board coordinates"
		>
			{coordinates}
		</p>
		<div class="flex flex-wrap items-center justify-between gap-3">
			<p class="flex items-baseline gap-3">
				<span class="text-display leading-none font-light">
					{(jobs?.total ?? 0).toLocaleString('en-US')}
				</span>
				<span class="coord text-muted">
					{(jobs?.total ?? 0) === 1 ? 'open role' : 'open roles'}
				</span>
			</p>
			<a href="/jobs/submit" class="link text-meta font-semibold">
				Know a missing role? Submit it
			</a>
		</div>

		{#if activeFilters.length > 0}
			<ul class="mt-3 flex flex-wrap items-center gap-1.5" aria-label="Active filters">
				{#each activeFilters as f (f.key + f.value)}
					<li>
						<a
							href={href(removeFilter(f.key, f.id ?? f.value))}
							class="btn btn-quiet is-on !py-1 text-coord"
						>
							{#if f.label}<span class="opacity-70">{f.label}:</span>{/if}
							{f.value}
							<span class="sr-only">— remove this filter</span>
							<svg width="11" height="11" viewBox="0 0 16 16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M3.5 3.5l9 9M12.5 3.5l-9 9"/></svg>
						</a>
					</li>
				{/each}
			</ul>
		{/if}

		<div class="mt-2 divide-y divide-rule">
			{#each jobs?.items ?? [] as job, i (job.id)}
				{#if i === unplacedStartIndex}
					<div class="col-span-full mt-2 flex items-center gap-3">
						<span class="h-px flex-1 bg-rule"></span>
						<span class="axis-label">
							Location not parsed — may still be in {selectedCountryName}
						</span>
						<span class="h-px flex-1 bg-rule"></span>
					</div>
				{/if}
				<JobStrip {job} {categoryNames} {onReport} />
			{:else}
				{#if data.boardUnavailable}
					<div class="py-20 text-center" role="alert">
						<p class="text-title font-semibold">We couldn't read the board just now.</p>
						<p class="mt-2 text-meta text-muted">
							This is our end, not your filters — the listings service didn't answer.
							Refresh in a moment and it should come back.
						</p>
					</div>
				{:else}
					<div class="py-20 text-center">
						<p class="text-title font-semibold">No roles match these filters.</p>
						<p class="mt-2 text-meta text-muted">
							Try widening a filter, or clear them and start again.
						</p>
						<a href="/jobs" class="btn btn-quiet mt-6">Clear all filters</a>
					</div>
				{/if}
			{/each}
		</div>

		{#if jobs}
			<Pagination data={jobs} makeHref={pageHref} />
		{/if}

		<div class="mt-10 flex flex-col gap-3">
			{#if openApplications && openApplications.total > 0}
				<Accordion
					title="Companies that invite speculative applications"
					count={openApplications.total}
				>
					<p class="text-meta text-muted">
						These companies accept speculative applications, so write to them directly even if
						nothing above matches. Any that also have roles on the board are marked.
					</p>
					<ul class="mt-4 grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
						{#each openApplications.companies as company (company.id)}
							<li class="flex items-center justify-between gap-3 p-3">
								<span class="min-w-0">
									<span class="block truncate text-meta font-semibold">{company.name}</span>
									<span class="coord block truncate text-muted">
										{company.category}
									</span>
									{#if company.open_roles > 0}
										<a
											href="/companies/{company.slug}"
											class="coord block truncate text-muted hover:text-accent hover:underline"
										>
											{company.open_roles} on the board
										</a>
									{/if}
								</span>
								{#if company.careers_url}
									<a
										href={company.careers_url}
										target="_blank"
										rel="noopener noreferrer"
										class="btn btn-quiet shrink-0 !px-2 !py-1 text-coord"
									>
										Apply
									</a>
								{/if}
							</li>
						{/each}
					</ul>
				</Accordion>
			{/if}

			{#if blocked && blocked.total > 0}
				<Accordion
					title="Companies worth checking yourself"
					count={blocked.total}
				>
					<p class="text-meta text-muted">
						These are companies we've checked by hand and can't read — some refuse automated
						readers outright, some draw their board with JavaScript, and some bury it in an
						embedded portal — so their roles never reach this board even though the careers page
						opens fine in a normal browser.
					</p>
					<div class="mt-3 p-3">
						<p class="text-meta">
							Searching <strong>"acoustic engineer"</strong> on
							<a
								href="https://www.linkedin.com/jobs/search/?keywords=acoustic%20engineer"
								target="_blank"
								rel="noopener noreferrer"
								class="font-semibold text-accent hover:underline"
							>
								LinkedIn
							</a>
							surfaces a lot of roles that never reach a company careers page.
						</p>
					</div>
					<ul class="mt-4 grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
						{#each blocked.companies as company (company.id)}
							<li class="flex items-center justify-between gap-3 p-3">
								<span class="min-w-0">
									<span class="block truncate text-meta font-semibold">{company.name}</span>
									<span class="coord block truncate text-muted">
										{company.category}
									</span>
								</span>
								{#if company.careers_url}
									<a
										href={company.careers_url}
										target="_blank"
										rel="noopener noreferrer"
										class="btn btn-quiet shrink-0 !px-2 !py-1 text-coord"
									>
										Careers
									</a>
								{/if}
							</li>
						{/each}
					</ul>
					<a
						href="/companies/blocked"
						class="link mt-4 inline-block text-meta font-semibold"
					>
						Why these are here →
					</a>
				</Accordion>
			{/if}
		</div>
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
