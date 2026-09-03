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

<section class="mt-6">
	<h1 class="legend">SUBMISSION QUEUE</h1>

	{#if message}
		<p class="panel mt-3 p-3 text-sm font-semibold" role="status">{message}</p>
	{/if}

	{#if loading}
		<p class="mt-4 font-mono text-sm text-ink-soft">Loading queue…</p>
	{:else if submissions.length === 0}
		<p class="panel mt-4 p-6 font-mono text-sm text-ink-soft">QUEUE EMPTY — nothing pending review.</p>
	{:else}
		<div class="mt-4 space-y-3">
			{#each submissions as s (s.id)}
				<article class="panel p-4">
					<div class="flex flex-wrap items-start justify-between gap-2">
						<div class="min-w-0">
							<h2 class="font-bold">{s.title}</h2>
							<p class="text-sm text-ink-soft">
								{s.company_name}{#if s.location} · {s.location}{/if}{#if s.remote} · remote{/if}
								· submitted {new Date(s.submitted_at).toLocaleDateString()}
								· requested: {s.requested_days != null ? `${s.requested_days} days` : 'default (30 days)'}
							</p>
						</div>
						<a href={s.url} target="_blank" rel="noopener noreferrer" class="btn-latch !normal-case !tracking-normal">
							Open posting ↗
						</a>
					</div>
					<p class="mt-2 line-clamp-3 max-w-3xl text-sm leading-relaxed text-ink-soft">{s.description}</p>
					<div class="mt-3 flex flex-wrap items-center gap-2">
						<button type="button" class="btn-primary !py-1.5" disabled={busyId === s.id} onclick={() => act(s.id, 'approve')}>
							Approve → live
						</button>
						<label class="flex items-center gap-1.5 text-xs text-ink-soft" for={`days-${s.id}`}>
							Days
							<input
								id={`days-${s.id}`}
								type="number"
								min="1"
								max="365"
								bind:value={overrideDays[s.id]}
								class="well h-8 w-16 px-2 font-mono text-xs"
							/>
						</label>
						<button
							type="button"
							class="btn-latch"
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
