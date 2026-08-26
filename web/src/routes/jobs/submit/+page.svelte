<script lang="ts">
	import jobCategories from '$lib/data/job-categories.json';
	import { submitJob, type SubmitState } from './actions';
	import type { JobSubmissionRequest } from './types';

	const categories = jobCategories.job_categories;

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
		submitter_email: ''
	});

	async function onSubmit(event: SubmitEvent) {
		event.preventDefault();
		submitState = { kind: 'submitting' };
		const cleaned: JobSubmissionRequest = {
			...form,
			url: form.url.trim()
		};
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
	<header class="panel p-5 sm:p-6">
		<h1 class="legend !text-sm">SUBMIT A JOB</h1>
		<p class="mt-3 text-lg font-bold tracking-tight">
			Put an audio role in front of the people who speak this language.
		</p>
		<p class="mt-1 text-sm text-ink-soft">
			Free for everyone — recruiters, founders, bandmates. Every submission is
			reviewed by a Young Audio Professionals moderator before it goes live, and
			listings expire after 30 days.
		</p>
	</header>

	{#if submitState.kind === 'success'}
		<div class="panel mt-4 p-6" role="status">
			<p class="flex items-center gap-2 font-mono text-sm font-semibold tracking-wide text-lit">
				<span class="inline-block h-2.5 w-2.5 rounded-full bg-lit"></span>
				SIGNAL RECEIVED
			</p>
			<h2 class="mt-2 text-lg font-bold">Thanks — your submission is in the review queue.</h2>
			<p class="mt-1 text-sm text-ink-soft">{submitState.message}</p>
			<div class="mt-4 flex gap-2">
				<button type="button" class="btn-latch" onclick={() => { submitState = { kind: 'idle' }; }}>
					Submit another
				</button>
				<a href="/jobs" class="btn-primary">Back to the board</a>
			</div>
		</div>
	{:else}
		<form class="panel mt-4 space-y-4 p-5 sm:p-6" onsubmit={onSubmit}>
			{#if submitState.kind === 'error'}
				<p class="rounded border !border-fader-deep bg-panel-recessed p-3 text-sm font-semibold" role="alert">
					{submitState.message}
				</p>
			{/if}

			<div class="grid gap-4 sm:grid-cols-2">
				<label class="block">
					<span class="mb-1 block font-mono text-[10px] tracking-[0.14em] text-ink-soft uppercase">Job title *</span>
					<input required maxlength="200" bind:value={form.title} class="well h-10 w-full px-3 text-sm" />
				</label>
				<label class="block">
					<span class="mb-1 block font-mono text-[10px] tracking-[0.14em] text-ink-soft uppercase">Company name *</span>
					<input required maxlength="200" bind:value={form.company_name} class="well h-10 w-full px-3 text-sm" />
				</label>
			</div>

			<label class="block">
				<span class="mb-1 block font-mono text-[10px] tracking-[0.14em] text-ink-soft uppercase">Apply URL *</span>
				<input required type="url" placeholder="https://…" maxlength="1000" bind:value={form.url} class="well h-10 w-full px-3 font-mono text-sm" />
			</label>

			<label class="block">
				<span class="mb-1 block font-mono text-[10px] tracking-[0.14em] text-ink-soft uppercase">Description *</span>
				<textarea required minlength="20" rows="7" bind:value={form.description} class="well w-full px-3 py-2 text-sm" placeholder="What the role is, who it's for, what a strong candidate looks like…"></textarea>
			</label>

			<div class="grid gap-4 sm:grid-cols-2">
				<label class="block">
					<span class="mb-1 block font-mono text-[10px] tracking-[0.14em] text-ink-soft uppercase">Location</span>
					<input maxlength="200" bind:value={form.location} placeholder="e.g. Nashville, TN" class="well h-10 w-full px-3 text-sm" />
				</label>
				<label class="block">
					<span class="mb-1 block font-mono text-[10px] tracking-[0.14em] text-ink-soft uppercase">Salary range</span>
					<input maxlength="100" bind:value={form.salary_range} placeholder="e.g. $80k–$110k" class="well h-10 w-full px-3 font-mono text-sm" />
				</label>
			</div>

			<div class="grid gap-4 sm:grid-cols-3">
				<label class="block">
					<span class="mb-1 block font-mono text-[10px] tracking-[0.14em] text-ink-soft uppercase">Type</span>
					<select bind:value={form.job_type} class="well h-10 w-full px-2 text-sm">
						<option value="">—</option>
						{#each ['full-time', 'part-time', 'contract', 'internship'] as t (t)}
							<option value={t}>{t}</option>
						{/each}
					</select>
				</label>
				<label class="block">
					<span class="mb-1 block font-mono text-[10px] tracking-[0.14em] text-ink-soft uppercase">Level</span>
					<select bind:value={form.experience_level} class="well h-10 w-full px-2 text-sm">
						<option value="">—</option>
						{#each ['entry', 'mid', 'senior', 'lead', 'manager'] as lvl (lvl)}
							<option value={lvl}>{lvl}</option>
						{/each}
					</select>
				</label>
				<label class="block">
					<span class="mb-1 block font-mono text-[10px] tracking-[0.14em] text-ink-soft uppercase">Specialty</span>
					<select bind:value={form.audio_domain} class="well h-10 w-full px-2 text-sm">
						<option value="">—</option>
						{#each categories as cat (cat.id)}
							<option value={cat.id}>{cat.name}</option>
						{/each}
					</select>
				</label>
			</div>

			<label class="flex items-center gap-2 text-sm font-semibold">
				<input type="checkbox" bind:checked={form.remote} class="h-4 w-4 accent-[#d96c2c]" />
				This role can be done remotely
			</label>

			<fieldset class="border-t border-seam pt-4">
				<legend class="font-mono text-[10px] tracking-[0.14em] text-ink-soft uppercase">
					You <span class="normal-case">(for moderator questions only — never published)</span>
				</legend>
				<div class="mt-3 grid gap-4 sm:grid-cols-2">
					<label class="block">
						<span class="mb-1 block font-mono text-[10px] tracking-[0.14em] text-ink-soft uppercase">Name</span>
						<input maxlength="200" bind:value={form.submitter_name} class="well h-10 w-full px-3 text-sm" autocomplete="name" />
					</label>
					<label class="block">
						<span class="mb-1 block font-mono text-[10px] tracking-[0.14em] text-ink-soft uppercase">Email</span>
						<input type="email" maxlength="320" bind:value={form.submitter_email} class="well h-10 w-full px-3 text-sm" autocomplete="email" />
					</label>
				</div>
			</fieldset>

			<button type="submit" disabled={submitState.kind === 'submitting'} class="btn-primary w-full !py-3 disabled:opacity-60">
				{submitState.kind === 'submitting' ? 'Sending…' : 'Send to the review queue'}
			</button>
			<p class="text-center font-mono text-[11px] tracking-wide text-ink-soft">
				Rate limited to 3 submissions per day per network.
			</p>
		</form>
	{/if}
</div>
