<script lang="ts">
	import { clientApi } from '$lib/client';

	interface JobFeedbackItem {
		id: number;
		job_id: number;
		job_title: string;
		company_name: string | null;
		kind: string;
		suggested_categories: string[] | null;
		comment: string | null;
		feature_days: number | null;
		feature_note: string | null;
		submitter_email: string | null;
		status: string;
		submitted_at: string;
		reviewed_at: string | null;
		reviewed_by: string | null;
		reject_reason: string | null;
	}

	interface FeatureTerms {
		days: number;
		indefinite: boolean;
		note: string;
	}

	interface SiteFeedbackItem {
		id: number;
		kind: string;
		company_name: string | null;
		company_url: string | null;
		comment: string | null;
		submitter_email: string | null;
		page_path: string | null;
		status: string;
		submitted_at: string;
		reviewed_at: string | null;
		reviewed_by: string | null;
		reject_reason: string | null;
	}

	interface CompanySuggestionItem {
		id: number;
		company_id: number;
		company_name: string | null;
		company_slug: string | null;
		careers_url: string | null;
		website_url: string | null;
		category: string | null;
		current_careers_url: string | null;
		current_website_url: string | null;
		current_category: string | null;
		description: string | null;
		links: { label: string; url: string }[] | null;
		headquarters: string | null;
		founded: number | null;
		comment: string | null;
		submitter_email: string | null;
		status: string;
		submitted_at: string;
	}

	const JOB_KIND_LABELS: Record<string, string> = {
		wrong_category: 'Wrong category',
		not_audio: 'Not an audio job',
		no_longer_available: 'No longer available',
		broken_description: 'Description looks broken',
		broken_link: 'Application link is broken',
		feature_request: 'Request to feature'
	};

	const SITE_KIND_LABELS: Record<string, string> = {
		company_suggestion: 'Suggest a company',
		general: 'General feedback'
	};

	let jobFeedback = $state<JobFeedbackItem[]>([]);
	let jobLoading = $state(true);
	let jobMessage = $state('');
	let jobBusyId = $state<number | null>(null);
	let featureTerms = $state<Record<number, FeatureTerms>>({});

	let siteFeedback = $state<SiteFeedbackItem[]>([]);
	let siteLoading = $state(true);
	let siteMessage = $state('');
	let siteBusyId = $state<number | null>(null);

	let companySuggestions = $state<CompanySuggestionItem[]>([]);
	let companyLoading = $state(true);
	let companyMessage = $state('');
	let companyBusyId = $state<number | null>(null);

	async function loadJobFeedback() {
		jobLoading = true;
		try {
			const result = await clientApi<{ items: JobFeedbackItem[] }>(
				'/api/admin/job-feedback?status=pending&per_page=50'
			);
			jobFeedback = result.items;
			featureTerms = Object.fromEntries(
				result.items
					.filter((f) => f.kind === 'feature_request')
					.map((f) => [
						f.id,
						{ days: f.feature_days ?? 30, indefinite: f.feature_days === null, note: f.feature_note ?? '' }
					])
			);
		} catch (err) {
			jobMessage = err instanceof Error ? err.message : 'Failed to load queue';
		} finally {
			jobLoading = false;
		}
	}

	async function loadSiteFeedback() {
		siteLoading = true;
		try {
			const result = await clientApi<{ items: SiteFeedbackItem[] }>(
				'/api/admin/site-feedback?status=pending&per_page=50'
			);
			siteFeedback = result.items;
		} catch (err) {
			siteMessage = err instanceof Error ? err.message : 'Failed to load queue';
		} finally {
			siteLoading = false;
		}
	}

	async function loadCompanySuggestions() {
		companyLoading = true;
		try {
			const result = await clientApi<{ items: CompanySuggestionItem[] }>(
				'/api/admin/company-suggestions?status=pending&per_page=50'
			);
			companySuggestions = result.items;
		} catch (err) {
			companyMessage = err instanceof Error ? err.message : 'Failed to load queue';
		} finally {
			companyLoading = false;
		}
	}

	$effect(() => {
		loadJobFeedback();
		loadSiteFeedback();
		loadCompanySuggestions();
	});

	async function actCompany(id: number, action: 'approve' | 'reject') {
		companyBusyId = id;
		companyMessage = '';
		try {
			const result = await clientApi<{ status: string; applied?: string }>(
				`/api/admin/company-suggestions/${id}/${action}`,
				{
					method: 'POST',
					body: action === 'reject' ? { reason: 'Rejected from admin console' } : {}
				}
			);
			await loadCompanySuggestions();
			companyMessage =
				action === 'approve'
					? `Suggestion #${id} approved${result.applied ? ` — ${result.applied}` : ''}.`
					: `Suggestion #${id} rejected.`;
		} catch (err) {
			companyMessage = err instanceof Error ? err.message : 'Action failed';
		} finally {
			companyBusyId = null;
		}
	}

	function approveBody(id: number): Record<string, unknown> {
		const terms = featureTerms[id];
		if (!terms) return {};
		return {
			feature_days: terms.indefinite ? null : terms.days,
			feature_indefinite: terms.indefinite,
			feature_note: terms.note.trim() || null
		};
	}

	async function actJob(id: number, action: 'approve' | 'reject') {
		jobBusyId = id;
		jobMessage = '';
		try {
			const result = await clientApi<{ status: string; applied?: string }>(
				`/api/admin/job-feedback/${id}/${action}`,
				{
					method: 'POST',
					body: action === 'reject' ? { reason: 'Rejected from admin console' } : approveBody(id)
				}
			);
			await loadJobFeedback();
			jobMessage =
				action === 'approve'
					? `Feedback #${id} approved${result.applied ? ` — ${result.applied}` : ''}.`
					: `Feedback #${id} rejected.`;
		} catch (err) {
			jobMessage = err instanceof Error ? err.message : 'Action failed';
		} finally {
			jobBusyId = null;
		}
	}

	async function actSite(id: number, action: 'resolve' | 'reject') {
		siteBusyId = id;
		siteMessage = '';
		try {
			await clientApi(`/api/admin/site-feedback/${id}/${action}`, {
				method: 'POST',
				body: action === 'reject' ? { reason: 'Rejected from admin console' } : {}
			});
			await loadSiteFeedback();
			siteMessage = `Feedback #${id} ${action === 'resolve' ? 'resolved' : 'rejected'}.`;
		} catch (err) {
			siteMessage = err instanceof Error ? err.message : 'Action failed';
		} finally {
			siteBusyId = null;
		}
	}
</script>

<section class="mt-10">
	<h1 class="text-title font-semibold">Job feedback queue</h1>

	{#if jobMessage}
		<p class="mt-4 text-meta font-semibold" role="status">{jobMessage}</p>
	{/if}

	{#if jobLoading}
		<p class="mt-6 text-meta text-muted">Loading queue…</p>
	{:else if jobFeedback.length === 0}
		<p class="mt-6 text-meta text-muted">Queue empty — nothing pending review.</p>
	{:else}
		<div class="mt-8 space-y-8">
			{#each jobFeedback as f (f.id)}
				<article class="border-t border-rule pt-8 first:border-0 first:pt-0">
					<div class="flex flex-wrap items-start justify-between gap-3">
						<div class="min-w-0">
							<h2 class="font-semibold">{f.job_title}</h2>
							<p class="mt-1 text-meta text-muted">
								{f.company_name ?? 'Unknown company'} · {JOB_KIND_LABELS[f.kind] ?? f.kind}
								· submitted {new Date(f.submitted_at).toLocaleDateString()}
							</p>
						</div>
						<a
							href="/jobs/{f.job_id}"
							target="_blank"
							rel="noopener noreferrer"
							class="btn btn-quiet"
						>
							Open listing<svg width="11" height="11" viewBox="0 0 16 16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M6 3h7v7M13 3L6.5 9.5M11 11v2H3V5h2"/></svg>
						</a>
					</div>
					{#if f.suggested_categories && f.suggested_categories.length > 0}
						<p class="mt-3 text-meta text-muted">
							<span class="axis-label">Suggested categories</span>
							{f.suggested_categories.join(', ')}
						</p>
					{/if}
					{#if f.comment}
						<p class="mt-3 max-w-3xl text-meta leading-relaxed text-muted">{f.comment}</p>
					{/if}
					{#if f.submitter_email}
						<p class="mt-2 text-meta text-muted">
							<span class="axis-label">From</span>
							{f.submitter_email}
						</p>
					{/if}
					{#if featureTerms[f.id]}
						<div class="mt-4 max-w-3xl space-y-3 border-l-2 border-accent pl-4">
							<p class="axis-label">
								Requested: {f.feature_days === null ? 'until filled (no end date)' : `${f.feature_days} days`}
								· edit before approving
							</p>
							<div class="flex flex-wrap items-center gap-x-5 gap-y-2">
								<label class="flex items-center gap-2 text-meta font-semibold">
									<input
										type="number"
										min="1"
										max="365"
										bind:value={featureTerms[f.id].days}
										disabled={featureTerms[f.id].indefinite}
										class="field h-9 w-20"
										aria-label="Days to feature"
									/>
									days
								</label>
								<label class="flex items-center gap-2 text-meta font-semibold">
									<input type="checkbox" bind:checked={featureTerms[f.id].indefinite} class="h-4 w-4 accent-accent" />
									No end date
								</label>
							</div>
							<label class="block">
								<span class="axis-label mb-1 block">Note shown on the listing (optional)</span>
								<textarea rows="2" maxlength="1000" bind:value={featureTerms[f.id].note} class="field"></textarea>
							</label>
						</div>
					{/if}
					<div class="mt-5 flex flex-wrap gap-3">
						<button
							type="button"
							class="btn btn-primary"
							disabled={jobBusyId === f.id}
							onclick={() => actJob(f.id, 'approve')}
						>
							{featureTerms[f.id] ? 'Approve and feature' : 'Approve and apply'}
						</button>
						<button
							type="button"
							class="btn btn-quiet"
							disabled={jobBusyId === f.id}
							onclick={() => actJob(f.id, 'reject')}
						>
							Reject
						</button>
					</div>
				</article>
			{/each}
		</div>
	{/if}
</section>

<section class="mt-16">
	<h2 class="text-title font-semibold">Site feedback queue</h2>

	{#if siteMessage}
		<p class="mt-4 text-meta font-semibold" role="status">{siteMessage}</p>
	{/if}

	{#if siteLoading}
		<p class="mt-6 text-meta text-muted">Loading queue…</p>
	{:else if siteFeedback.length === 0}
		<p class="mt-6 text-meta text-muted">Queue empty — nothing pending review.</p>
	{:else}
		<div class="mt-8 space-y-8">
			{#each siteFeedback as f (f.id)}
				<article class="border-t border-rule pt-8 first:border-0 first:pt-0">
					<div class="flex flex-wrap items-start justify-between gap-3">
						<div class="min-w-0">
							<h3 class="font-semibold">{SITE_KIND_LABELS[f.kind] ?? f.kind}</h3>
							<p class="mt-1 text-meta text-muted">
								{#if f.company_name}{f.company_name} · {/if}
								submitted {new Date(f.submitted_at).toLocaleDateString()}
								{#if f.page_path} · from {f.page_path}{/if}
							</p>
						</div>
						{#if f.company_url}
							<a
								href={f.company_url}
								target="_blank"
								rel="noopener noreferrer"
								class="btn btn-quiet"
							>
								Open link<svg width="11" height="11" viewBox="0 0 16 16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M6 3h7v7M13 3L6.5 9.5M11 11v2H3V5h2"/></svg>
							</a>
						{/if}
					</div>
					{#if f.comment}
						<p class="mt-3 max-w-3xl text-meta leading-relaxed text-muted">{f.comment}</p>
					{/if}
					{#if f.submitter_email}
						<p class="mt-2 text-meta text-muted">
							<span class="axis-label">From</span>
							{f.submitter_email}
						</p>
					{/if}
					<div class="mt-5 flex flex-wrap gap-3">
						<button
							type="button"
							class="btn btn-primary"
							disabled={siteBusyId === f.id}
							onclick={() => actSite(f.id, 'resolve')}
						>
							Resolve
						</button>
						<button
							type="button"
							class="btn btn-quiet"
							disabled={siteBusyId === f.id}
							onclick={() => actSite(f.id, 'reject')}
						>
							Reject
						</button>
					</div>
				</article>
			{/each}
		</div>
	{/if}
</section>

<section class="mt-16">
	<h2 class="text-title font-semibold">Company info suggestions</h2>

	{#if companyMessage}
		<p class="mt-4 text-meta font-semibold" role="status">{companyMessage}</p>
	{/if}

	{#if companyLoading}
		<p class="mt-6 text-meta text-muted">Loading queue…</p>
	{:else if companySuggestions.length === 0}
		<p class="mt-6 text-meta text-muted">Queue empty — nothing pending review.</p>
	{:else}
		<div class="mt-8 space-y-8">
			{#each companySuggestions as s (s.id)}
				<article class="border-t border-rule pt-8 first:border-0 first:pt-0">
					<div class="flex flex-wrap items-start justify-between gap-3">
						<div class="min-w-0">
							<h3 class="font-semibold">{s.company_name ?? `Company #${s.company_id}`}</h3>
							<p class="mt-1 text-meta text-muted">
								submitted {new Date(s.submitted_at).toLocaleDateString()}
							</p>
						</div>
						{#if s.company_slug}
							<a
								href="/companies/{s.company_slug}"
								target="_blank"
								rel="noopener noreferrer"
								class="btn btn-quiet"
							>
								Open profile<svg width="11" height="11" viewBox="0 0 16 16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M6 3h7v7M13 3L6.5 9.5M11 11v2H3V5h2"/></svg>
							</a>
						{/if}
					</div>
					{#if s.careers_url || s.website_url || s.category}
						<dl class="mt-3 max-w-3xl space-y-2 border-l-2 border-accent pl-4 text-meta">
							{#each [
								{ label: 'Careers page', from: s.current_careers_url, to: s.careers_url, url: true },
								{ label: 'Website', from: s.current_website_url, to: s.website_url, url: true },
								{ label: 'Category', from: s.current_category, to: s.category, url: false }
							].filter((row) => row.to) as row (row.label)}
								<div class="min-w-0">
									<dt class="axis-label">{row.label}</dt>
									<dd class="coord min-w-0 wrap-anywhere">
										<span class="text-muted line-through">{row.from ?? 'none'}</span>
										<span aria-hidden="true"> → </span>
										{#if row.url}
											<a href={row.to} target="_blank" rel="noopener noreferrer" class="link">{row.to}</a>
										{:else}
											<span class="font-semibold">{row.to}</span>
										{/if}
									</dd>
								</div>
							{/each}
							{#if s.careers_url}
								<p class="text-coord text-muted">
									Approving clears the stored job-board binding so the next scrape re-detects it.
									Open the link first, then scrape the company to confirm.
								</p>
							{/if}
						</dl>
					{/if}
					{#if s.description}
						<p class="mt-3 max-w-3xl text-meta leading-relaxed text-muted">{s.description}</p>
					{/if}
					{#if s.links && s.links.length > 0}
						<ul class="mt-3 space-y-1">
							{#each s.links as link (link.url)}
								<li class="flex min-w-0 items-baseline gap-2 text-meta">
									<span class="shrink-0 font-semibold">{link.label}</span>
									<span class="coord min-w-0 truncate text-muted">{link.url}</span>
								</li>
							{/each}
						</ul>
					{/if}
					{#if s.headquarters || s.founded}
						<p class="mt-3 text-meta text-muted">
							{#if s.headquarters}<span class="axis-label">HQ</span> {s.headquarters}{/if}
							{#if s.headquarters && s.founded} · {/if}
							{#if s.founded}<span class="axis-label">Founded</span> {s.founded}{/if}
						</p>
					{/if}
					{#if s.comment}
						<p class="mt-3 max-w-3xl text-meta leading-relaxed text-muted">{s.comment}</p>
					{/if}
					{#if s.submitter_email}
						<p class="mt-2 text-meta text-muted">
							<span class="axis-label">From</span>
							{s.submitter_email}
						</p>
					{/if}
					<div class="mt-5 flex flex-wrap gap-3">
						<button
							type="button"
							class="btn btn-primary"
							disabled={companyBusyId === s.id}
							onclick={() => actCompany(s.id, 'approve')}
						>
							Approve and apply
						</button>
						<button
							type="button"
							class="btn btn-quiet"
							disabled={companyBusyId === s.id}
							onclick={() => actCompany(s.id, 'reject')}
						>
							Reject
						</button>
					</div>
				</article>
			{/each}
		</div>
	{/if}
</section>
