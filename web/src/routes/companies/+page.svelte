<script lang="ts">
	import { page } from '$app/state';
	import Pagination from '$lib/components/Pagination.svelte';
	import type { Paginated, CompanyRecord } from '$lib/types';

	let { data } = $props();

	const companies: Paginated<CompanyRecord> | null = $derived(data.companies);
	const params = $derived(data.params as Record<string, string>);

	const categoryOptions = $derived(data.categories?.categories ?? []);

	const SORTS: [string, string][] = [
		['board-desc', 'Most roles'],
		['name-asc', 'Name A–Z']
	];

	function boardLabel(count: number): string {
		return count > 0 ? `${count.toLocaleString('en-US')} on the board` : 'no open roles';
	}

	function href(overrides: Record<string, string | undefined>): string {
		const next = new URLSearchParams(page.url.searchParams);
		for (const [key, value] of Object.entries(overrides)) {
			if (value === undefined || value === '') next.delete(key);
			else next.set(key, value);
		}
		next.delete('page');
		const qs = next.toString();
		return qs ? `/companies?${qs}` : '/companies';
	}

	function pageHref(p: number): string {
		const next = new URLSearchParams(page.url.searchParams);
		next.set('page', String(p));
		return `/companies?${next.toString()}`;
	}

	const sortCarry = $derived.by(() => {
		const out: [string, string][] = [];
		for (const [key, value] of page.url.searchParams) {
			if (key === 'sort' || key === 'page' || !value) continue;
			out.push([key, value]);
		}
		return out;
	});

	const activeFilters = $derived.by(() => {
		const labels: { key: string; label: string; value: string }[] = [];
		if (params.q) labels.push({ key: 'q', label: 'Search', value: `“${params.q}”` });
		if (params.category) labels.push({ key: 'category', label: 'Category', value: params.category });
		if (params.hiring_only) labels.push({ key: 'hiring_only', label: '', value: 'Hiring only' });
		return labels;
	});

	const coordinates = $derived.by(() => {
		const parts: string[] = [`${(companies?.total ?? 0).toLocaleString('en-US')} companies`];
		parts.push(params.category ? `cat ${params.category}` : `cat all`);
		if (params.hiring_only) parts.push('hiring only');
		parts.push(`sort ${params.sort === 'name-asc' ? 'name' : 'board'}`);
		if ((companies?.pages ?? 1) > 1) parts.push(`p${data.page}/${companies?.pages ?? 1}`);
		return parts.join(' · ');
	});
</script>

<svelte:head>
	<title>Company directory | ASoundJob</title>
	<meta
		name="description"
		content="Browse every audio company ASoundJob indexes — filter by specialty and see who has open roles on the board right now."
	/>
	<link rel="canonical" href="{data.siteUrl}/companies" />
</svelte:head>

<h1 class="sr-only">Company directory</h1>

<div class="mt-6 grid gap-6 lg:grid-cols-[17rem_minmax(0,1fr)]">
	<form
		method="get"
		action="/companies"
		class="h-fit min-w-0 lg:sticky lg:top-24"
		aria-label="Company filters"
	>
		<h2 class="text-title font-semibold">Filters</h2>

		<label class="mt-4 block">
			<span class="axis-label mb-2 block">Search</span>
			<input
				name="q"
				type="search"
				value={params.q ?? ''}
				placeholder="Company name…"
				class="field"
			/>
		</label>

		<fieldset class="mt-4">
			<legend class="axis-label mb-2">Category</legend>
			<select name="category" class="field">
				<option value="">All categories</option>
				{#each categoryOptions as cat (cat.name)}
					<option value={cat.name} selected={params.category === cat.name}>
						{cat.name} ({cat.company_count})
					</option>
				{/each}
			</select>
		</fieldset>

		<fieldset class="mt-4">
			<label class="flex items-center gap-2 text-meta font-semibold">
				<input
					type="checkbox"
					name="hiring_only"
					value="true"
					checked={params.hiring_only === 'true'}
					class="h-4 w-4 accent-accent"
				/>
				Hiring only
			</label>
		</fieldset>

		{#if params.sort}
			<input type="hidden" name="sort" value={params.sort} />
		{/if}

		<div class="mt-4 flex items-center gap-2">
			<button type="submit" class="btn btn-primary flex-1">Apply</button>
			<a href="/companies" class="btn btn-quiet">Reset</a>
		</div>
	</form>

	<section class="min-w-0" aria-label="Company results">
		<p
			class="coord sticky top-16 z-30 -mx-1 mb-4 truncate border-b border-muted bg-ground/95 px-1 py-2 backdrop-blur"
			aria-live="polite"
			aria-label="Current directory coordinates"
		>
			{coordinates}
		</p>

		<div class="flex flex-wrap items-end justify-between gap-x-6 gap-y-3">
			<p class="flex items-baseline gap-3">
				<span class="text-display leading-none font-light">
					{(companies?.total ?? 0).toLocaleString('en-US')}
				</span>
				<span class="coord text-muted">
					{(companies?.total ?? 0) === 1 ? 'company' : 'companies'}
				</span>
			</p>

			<form method="get" action="/companies" class="flex items-center gap-2">
				{#each sortCarry as [key, value], i (key + i)}
					<input type="hidden" name={key} value={value} />
				{/each}
				<label class="axis-label shrink-0" for="sort-select">Sort</label>
				<select
					id="sort-select"
					name="sort"
					class="field w-auto"
					onchange={(e) => e.currentTarget.form?.requestSubmit()}
				>
					{#each SORTS as [value, labelText] (value)}
						<option {value} selected={(params.sort ?? 'board-desc') === value}>{labelText}</option>
					{/each}
				</select>
				<noscript>
					<button type="submit" class="btn btn-quiet">Go</button>
				</noscript>
			</form>
		</div>

		{#if activeFilters.length > 0}
			<ul class="mt-3 flex flex-wrap items-center gap-1.5" aria-label="Active filters">
				{#each activeFilters as f (f.key)}
					<li>
						<a href={href({ [f.key]: undefined })} class="btn btn-quiet is-on !py-1 text-coord">
							{#if f.label}<span class="opacity-70">{f.label}:</span>{/if}
							{f.value}
							<span class="sr-only">— remove this filter</span>
							<svg width="11" height="11" viewBox="0 0 16 16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M3.5 3.5l9 9M12.5 3.5l-9 9"/></svg>
						</a>
					</li>
				{/each}
			</ul>
		{/if}

		<div class="@container mt-4">
			<div class="grid items-stretch gap-3 @3xl:grid-cols-2 @6xl:grid-cols-3">
				{#each companies?.items ?? [] as company (company.id)}
					<article class="flex min-w-0 flex-col border border-rule bg-ground p-4 transition-colors hover:border-muted sm:p-5">
						<div class="flex items-start gap-2">
							<h3 class="min-w-0 flex-1 text-title font-semibold leading-tight text-balance wrap-anywhere">
								<a href="/companies/{company.slug}" class="line-clamp-2 hover:text-accent hover:underline">
									{company.name}
								</a>
							</h3>
							{#if company.verified}
								<span class="coord shrink-0 font-bold text-muted">verified</span>
							{/if}
						</div>

						<p class="mt-1 truncate text-meta text-muted">
							{company.category}{company.headquarters ? ` · ${company.headquarters}` : ''}
						</p>

						<p class="coord mt-3 {company.board_jobs_count > 0 ? 'font-bold text-ink' : 'text-muted'}">
							{boardLabel(company.board_jobs_count)}
						</p>

						<div class="mt-auto flex items-center gap-2 pt-3">
							{#if company.board_jobs_count > 0}
								<a href="/companies/{company.slug}" class="btn btn-quiet !py-1 text-coord">
									View roles
								</a>
							{:else if company.careers_url}
								<a
									href={company.careers_url}
									target="_blank"
									rel="noopener noreferrer"
									class="btn btn-quiet !py-1 text-coord"
								>
									Careers site
								</a>
							{/if}
						</div>
					</article>
				{:else}
					{#if data.boardUnavailable}
						<div class="col-span-full py-20 text-center" role="alert">
							<p class="text-title font-semibold">We couldn't read the directory just now.</p>
							<p class="mt-2 text-meta text-muted">
								This is our end, not your filters — the company service didn't answer. Refresh in
								a moment and it should come back.
							</p>
						</div>
					{:else}
						<div class="col-span-full py-20 text-center">
							<p class="text-title font-semibold">No companies match these filters.</p>
							<p class="mt-2 text-meta text-muted">
								Try widening a filter, or clear them and start again.
							</p>
							<a href="/companies" class="btn btn-quiet mt-6">Clear all filters</a>
						</div>
					{/if}
				{/each}
			</div>
		</div>

		{#if companies}
			<Pagination data={companies} makeHref={pageHref} />
		{/if}
	</section>
</div>
