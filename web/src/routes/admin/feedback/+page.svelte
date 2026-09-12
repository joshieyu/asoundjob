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
		submitter_email: string | null;
		status: string;
		submitted_at: string;
		reviewed_at: string | null;
		reviewed_by: string | null;
		reject_reason: string | null;
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

	const JOB_KIND_LABELS: Record<string, string> = {
		wrong_category: 'Wrong category',
		not_audio: 'Not an audio job',
		no_longer_available: 'No longer available',
		broken_description: 'Description looks broken',
		broken_link: 'Application link is broken'
	};

	const SITE_KIND_LABELS: Record<string, string> = {
		company_suggestion: 'Suggest a company',
		general: 'General feedback'
	};

	let jobFeedback = $state<JobFeedbackItem[]>([]);
	let jobLoading = $state(true);
	let jobMessage = $state('');
	let jobBusyId = $state<number | null>(null);

	let siteFeedback = $state<SiteFeedbackItem[]>([]);
	let siteLoading = $state(true);
	let siteMessage = $state('');
	let siteBusyId = $state<number | null>(null);

	async function loadJobFeedback() {
		jobLoading = true;
		try {
			const result = await clientApi<{ items: JobFeedbackItem[] }>(
				'/api/admin/job-feedback?status=pending&per_page=50'
			);
			jobFeedback = result.items;
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

	$effect(() => {
		loadJobFeedback();
		loadSiteFeedback();
	});

	async function actJob(id: number, action: 'approve' | 'reject') {
		jobBusyId = id;
		jobMessage = '';
		try {
			const result = await clientApi<{ status: string; applied?: string }>(
				`/api/admin/job-feedback/${id}/${action}`,
				{
					method: 'POST',
					body: action === 'reject' ? { reason: 'Rejected from admin console' } : {}
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
					<div class="mt-5 flex flex-wrap gap-3">
						<button
							type="button"
							class="btn btn-primary"
							disabled={jobBusyId === f.id}
							onclick={() => actJob(f.id, 'approve')}
						>
							Approve and apply
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
