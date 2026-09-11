<script lang="ts">
	import { clientApi } from '$lib/client';

	interface Submission {
		id: number;
		company_name: string;
		title: string;
		description: string;
		url: string;
		location: string | null;
		remote: boolean;
		job_type: string | null;
		salary_range: string | null;
		experience_level: string | null;
		audio_domain: string | null;
		status: string;
		submitted_at: string;
		requested_days: number | null;
	}

	let submissions = $state<Submission[]>([]);
	let loading = $state(true);
	let message = $state('');
	let busyId = $state<number | null>(null);
	let overrideDays = $state<Record<number, number | undefined>>({});

	async function load() {
		loading = true;
		try {
			const result = await clientApi<{ items: Submission[] }>(
				'/api/admin/submissions?status=pending&per_page=50'
			);
			submissions = result.items;
			for (const s of submissions) {
				overrideDays[s.id] = s.requested_days ?? undefined;
			}
		} catch (err) {
			message = err instanceof Error ? err.message : 'Failed to load queue';
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		load();
	});

	async function act(id: number, action: 'approve' | 'reject') {
		busyId = id;
		message = '';
		try {
			let body: Record<string, unknown> = {};
			if (action === 'reject') {
				body = { reason: 'Rejected from admin console' };
			} else if (overrideDays[id] != null) {
				body = { expires_days: overrideDays[id] };
			}
			await clientApi(`/api/admin/submissions/${id}/${action}`, {
				method: 'POST',
				body
			});
			await load();
			message = `Submission #${id} ${action}d.`;
		} catch (err) {
			message = err instanceof Error ? err.message : 'Action failed';
		} finally {
			busyId = null;
		}
	}
</script>

<section class="mt-10">
	<h1 class="text-title font-semibold">Submission queue</h1>

	{#if message}
		<p class="mt-4 text-meta font-semibold" role="status">{message}</p>
	{/if}

	{#if loading}
		<p class="mt-6 text-meta text-muted">Loading queue…</p>
	{:else if submissions.length === 0}
		<p class="mt-6 text-meta text-muted">Queue empty — nothing pending review.</p>
	{:else}
		<div class="mt-8 space-y-8">
			{#each submissions as s (s.id)}
				<article class="border-t border-rule pt-8 first:border-0 first:pt-0">
					<div class="flex flex-wrap items-start justify-between gap-3">
						<div class="min-w-0">
							<h2 class="font-semibold">{s.title}</h2>
							<p class="mt-1 text-meta text-muted">
								{s.company_name}{#if s.location} · {s.location}{/if}{#if s.remote} · remote{/if}
								· submitted {new Date(s.submitted_at).toLocaleDateString()}
								· requested: {s.requested_days != null ? `${s.requested_days} days` : 'default (30 days)'}
							</p>
						</div>
						<a href={s.url} target="_blank" rel="noopener noreferrer" class="btn btn-quiet">
							Open posting<svg width="11" height="11" viewBox="0 0 16 16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M6 3h7v7M13 3L6.5 9.5M11 11v2H3V5h2"/></svg>
						</a>
					</div>
					<p class="mt-3 line-clamp-3 max-w-3xl text-meta leading-relaxed text-muted">{s.description}</p>
					<div class="mt-5 flex flex-wrap items-center gap-3">
						<button type="button" class="btn btn-primary" disabled={busyId === s.id} onclick={() => act(s.id, 'approve')}>
							Approve and publish
						</button>
						<label class="flex items-center gap-2 text-meta text-muted" for={`days-${s.id}`}>
							Days
							<input
								id={`days-${s.id}`}
								type="number"
								min="1"
								max="365"
								bind:value={overrideDays[s.id]}
								class="field h-8 w-16"
							/>
						</label>
						<button
							type="button"
							class="btn btn-quiet"
							disabled={busyId === s.id}
							onclick={() => act(s.id, 'reject')}
						>
							Reject
						</button>
					</div>
				</article>
			{/each}
		</div>
	{/if}
</section>
