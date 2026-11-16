<script lang="ts">
	import { submitJob, type SubmitState } from './actions';
	import type { JobSubmissionRequest } from './types';

	let { data } = $props();

	const categories = $derived(data.categories?.categories ?? []);

	let submitState = $state<SubmitState>({ kind: 'idle' });
	let form: JobSubmissionRequest = $state({
		title: '',
		company_name: '',
		url: '',
		description: '',
		location: '',
		remote: false,
		job_type: '',
		salary_range: '',
		experience_level: '',
		audio_domain: '',
		submitter_name: '',
		submitter_email: '',
		duration_days: undefined,
		feature_requested: false,
		feature_days: 30,
		feature_indefinite: false,
		feature_note: ''
	});

	async function onSubmit(event: SubmitEvent) {
		event.preventDefault();
		submitState = { kind: 'submitting' };
		const cleaned: JobSubmissionRequest = {
			...form,
			url: form.url.trim()
		};
		if (!form.feature_requested) {
			delete cleaned.feature_days;
			delete cleaned.feature_note;
			cleaned.feature_indefinite = false;
		} else if (form.feature_indefinite) {
			delete cleaned.feature_days;
		}
		for (const key of Object.keys(cleaned) as (keyof JobSubmissionRequest)[]) {
			if (typeof cleaned[key] === 'string' && (cleaned[key] as string).trim() === '') {
				delete cleaned[key];
			}
		}
		submitState = await submitJob(cleaned);
	}
</script>

<svelte:head>
	<title>Submit a job | ASoundJob</title>
	<meta
		name="description"
		content="Submit an audio industry job to ASoundJob. Free, reviewed by moderators, live within days."
	/>
</svelte:head>

<div class="mx-auto mt-6 max-w-2xl">
	<header class="p-5 sm:p-6">
		<h1 class="text-title font-semibold">Submit a job</h1>
		<p class="mt-3 text-title font-bold tracking-tight">
			Put an audio role in front of passionate audio engineers.
		</p>
		<p class="mt-1 text-meta text-muted">
			Free for everyone. Every submission is
			reviewed by a Young Audio Professionals moderator before it goes live.
		</p>
	</header>

	{#if submitState.kind === 'success'}
		<div class="mt-4 p-6" role="status">
			<p class="flex items-center gap-2 text-meta font-semibold text-ink">
				<span class="inline-block h-2.5 w-2.5 rounded-full bg-accent"></span>
				Received
			</p>
			<h2 class="mt-2 text-title font-bold">Thanks — your submission is in the review queue.</h2>
			<p class="mt-1 text-meta text-muted">{submitState.message}</p>
			<div class="mt-4 flex gap-2">
				<button type="button" class="btn btn-quiet" onclick={() => { submitState = { kind: 'idle' }; }}>
					Submit another
				</button>
				<a href="/jobs" class="btn btn-primary">Back to the board</a>
			</div>
		</div>
	{:else}
		<form class="mt-4 space-y-4 p-5 sm:p-6" onsubmit={onSubmit}>
			{#if submitState.kind === 'error'}
				<p class="border border-ink bg-ground-tint p-3 text-meta font-semibold" role="alert">
					{submitState.message}
				</p>
			{/if}

			<div class="grid gap-4 sm:grid-cols-2">
				<label class="block">
					<span class="axis-label mb-2 block">Job title *</span>
					<input required maxlength="200" bind:value={form.title} class="field" />
				</label>
				<label class="block">
					<span class="axis-label mb-2 block">Company name *</span>
					<input required maxlength="200" bind:value={form.company_name} class="field" />
				</label>
			</div>

			<label class="block">
				<span class="axis-label mb-2 block">Apply URL *</span>
				<input required type="url" placeholder="https://…" maxlength="1000" bind:value={form.url} class="field coord" />
			</label>

			<label class="block">
				<span class="axis-label mb-2 block">Description *</span>
				<textarea required minlength="20" rows="7" bind:value={form.description} class="field" placeholder="What the role is, who it's for, what a strong candidate looks like…"></textarea>
			</label>

			<div class="grid gap-4 sm:grid-cols-2">
				<label class="block">
					<span class="axis-label mb-2 block">Location</span>
					<input maxlength="200" bind:value={form.location} placeholder="e.g. Nashville, TN" class="field" />
				</label>
				<label class="block">
					<span class="axis-label mb-2 block">Salary range</span>
					<input maxlength="100" bind:value={form.salary_range} placeholder="e.g. $80k–$110k" class="field coord" />
				</label>
				<label class="block">
					<span class="axis-label mb-2 block">How long should this stay up? (days)</span>
					<input type="number" min="1" max="365" bind:value={form.duration_days} placeholder="30" class="field" />
					<span class="mt-1 block text-coord text-muted">Defaults to 30 days if left blank.</span>
				</label>
			</div>

			<div class="grid gap-4 sm:grid-cols-3">
				<label class="block">
					<span class="axis-label mb-2 block">Type</span>
					<select bind:value={form.job_type} class="field">
						<option value="">—</option>
						{#each ['full-time', 'part-time', 'contract', 'temporary'] as t (t)}
							<option value={t}>{t}</option>
						{/each}
					</select>
				</label>
				<label class="block">
					<span class="axis-label mb-2 block">Level</span>
					<select bind:value={form.experience_level} class="field">
						<option value="">—</option>
						{#each ['internship', 'entry', 'mid', 'senior', 'lead', 'manager'] as lvl (lvl)}
							<option value={lvl}>{lvl}</option>
						{/each}
					</select>
				</label>
				<label class="block">
					<span class="axis-label mb-2 block">Specialty</span>
					<select bind:value={form.audio_domain} class="field">
						<option value="">—</option>
						{#each categories as cat (cat.id)}
							<option value={cat.id}>{cat.name}</option>
						{/each}
					</select>
				</label>
			</div>

			<label class="flex items-center gap-2 text-meta font-semibold">
				<input type="checkbox" bind:checked={form.remote} class="h-4 w-4 accent-accent" />
				This role can be done remotely
			</label>

			<fieldset class="border-t border-rule pt-4">
				<legend class="sr-only">Featuring</legend>
				<label class="flex items-start gap-2 text-meta font-semibold">
					<input type="checkbox" bind:checked={form.feature_requested} class="mt-0.5 h-4 w-4 accent-accent" />
					<span>
						Also request a feature on the front page
						<span class="mt-0.5 block font-normal text-muted">
							Featured roles sit above the fresh listings. The team decides, and may adjust the length or note.
						</span>
					</span>
				</label>
				{#if form.feature_requested}
					<div class="mt-4 space-y-4 border-l-2 border-accent pl-4">
						<div class="flex flex-wrap items-end gap-x-5 gap-y-3">
							<label class="block">
								<span class="axis-label mb-2 block">Feature for (days)</span>
								<input
									type="number"
									min="1"
									max="365"
									bind:value={form.feature_days}
									disabled={form.feature_indefinite}
									required={!form.feature_indefinite}
									class="field w-28"
								/>
							</label>
							<label class="flex h-10 items-center gap-2 text-meta font-semibold">
								<input type="checkbox" bind:checked={form.feature_indefinite} class="h-4 w-4 accent-accent" />
								Until it's filled (no end date)
							</label>
						</div>
						<label class="block">
							<span class="axis-label mb-2 block">Note to show on the listing (optional)</span>
							<textarea
								rows="2"
								maxlength="1000"
								bind:value={form.feature_note}
								class="field"
								placeholder="e.g. Hiring ASAP — questions to jane@studio.com"
							></textarea>
						</label>
					</div>
				{/if}
			</fieldset>

			<fieldset class="border-t border-rule pt-4">
				<legend class="axis-label">
					You <span class="normal-case">(for moderator questions only — never published)</span>
				</legend>
				<div class="mt-3 grid gap-4 sm:grid-cols-2">
					<label class="block">
						<span class="axis-label mb-2 block">Name</span>
						<input maxlength="200" bind:value={form.submitter_name} class="field" autocomplete="name" />
					</label>
					<label class="block">
						<span class="axis-label mb-2 block">Email</span>
						<input type="email" maxlength="320" bind:value={form.submitter_email} class="field" autocomplete="email" />
					</label>
				</div>
			</fieldset>

			<button type="submit" disabled={submitState.kind === 'submitting'} class="btn btn-primary w-full !py-3">
				{submitState.kind === 'submitting' ? 'Sending…' : 'Send to the review queue'}
			</button>
			<p class="text-center coord tracking-wide text-muted">
				Rate limited to 3 submissions per day per network.
			</p>
		</form>
	{/if}
</div>
