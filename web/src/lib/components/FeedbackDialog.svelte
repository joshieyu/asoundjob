<script lang="ts">
	import {
		submitJobFeedback,
		submitSiteFeedback,
		type FeedbackKindOption,
		type FeedbackState,
		type JobFeedbackKind,
		type SiteFeedbackKind
	} from '$lib/feedback';

	let {
		mode,
		jobId,
		jobTitle,
		kinds,
		categories = [],
		pagePath,
		open = $bindable(false)
	}: {
		mode: 'job' | 'site';
		jobId?: number;
		jobTitle?: string;
		kinds: FeedbackKindOption[];
		categories?: { id: string; name: string }[];
		pagePath?: string;
		open?: boolean;
	} = $props();

	let dialogEl: HTMLDialogElement | undefined = $state();
	let selectedKind = $state('');
	let selectedCategories = $state<string[]>([]);
	let comment = $state('');
	let email = $state('');
	let companyName = $state('');
	let companyUrl = $state('');
	let feedbackState = $state<FeedbackState>({ kind: 'idle' });

	$effect(() => {
		if (!dialogEl) return;
		if (open && !dialogEl.open) {
			selectedKind = kinds[0]?.value ?? '';
			selectedCategories = [];
			comment = '';
			email = '';
			companyName = '';
			companyUrl = '';
			feedbackState = { kind: 'idle' };
			dialogEl.showModal();
		} else if (!open && dialogEl.open) {
			dialogEl.close();
		}
	});

	function requestClose() {
		open = false;
	}

	function onBackdropClick(event: MouseEvent) {
		if (event.target === dialogEl) requestClose();
	}

	function toggleCategory(id: string, checked: boolean) {
		if (checked) {
			if (!selectedCategories.includes(id)) selectedCategories = [...selectedCategories, id];
		} else {
			selectedCategories = selectedCategories.filter((c) => c !== id);
		}
	}

	const showCategoryPicker = $derived(
		mode === 'job' && selectedKind === 'wrong_category' && categories.length > 0
	);

	const canSubmit = $derived.by(() => {
		if (feedbackState.kind === 'submitting') return false;
		if (mode === 'job') {
			if (selectedKind === 'wrong_category') {
				return selectedCategories.length > 0 || comment.trim().length > 0;
			}
			return true;
		}
		if (selectedKind === 'company_suggestion') return companyName.trim().length > 0;
		if (selectedKind === 'general') return comment.trim().length >= 5;
		return true;
	});

	async function onSubmit(event: SubmitEvent) {
		event.preventDefault();
		if (!canSubmit) return;
		feedbackState = { kind: 'submitting' };
		if (mode === 'job' && jobId !== undefined) {
			feedbackState = await submitJobFeedback(jobId, {
				kind: selectedKind as JobFeedbackKind,
				suggested_categories:
					selectedKind === 'wrong_category' && selectedCategories.length > 0
						? selectedCategories
						: null,
				comment: comment.trim() || null,
				submitter_email: email.trim() || null
			});
		} else {
			feedbackState = await submitSiteFeedback({
				kind: selectedKind as SiteFeedbackKind,
				company_name: companyName.trim() || null,
				company_url: companyUrl.trim() || null,
				comment: comment.trim() || null,
				submitter_email: email.trim() || null,
				page_path: pagePath ?? null
			});
		}
	}
</script>

<dialog
	bind:this={dialogEl}
	onclose={requestClose}
	onclick={onBackdropClick}
	class="m-auto w-[min(92vw,32rem)] border-rule p-0 backdrop:bg-ink/40"
	aria-labelledby="feedback-dialog-title"
>
	<div class="p-5 sm:p-6">
		<div class="flex items-start justify-between gap-3">
			<div class="min-w-0">
				<h2 id="feedback-dialog-title" class="mt-1 truncate text-title font-bold">
					{mode === 'job' ? (jobTitle ?? 'This listing') : 'Help us improve ASoundJob'}
				</h2>
			</div>
			<button
				type="button"
				class="flex h-7 w-7 shrink-0 items-center justify-center border border-rule bg-ground text-muted hover:text-accent"
				aria-label="Close dialog"
				onclick={requestClose}
			>
				<svg width="13" height="13" viewBox="0 0 16 16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><path d="M3.5 3.5l9 9M12.5 3.5l-9 9"/></svg>
			</button>
		</div>

		{#if feedbackState.kind === 'success'}
			<div class="mt-4" role="status">
				<p class="flex items-center gap-2 text-meta font-semibold text-ink">
					<span class="inline-block h-2.5 w-2.5 rounded-full bg-accent"></span>
					Received
				</p>
				<p class="mt-2 text-meta text-muted">{feedbackState.message}</p>
				<div class="mt-4 flex justify-end">
					<button type="button" class="btn btn-primary" onclick={requestClose}>Done</button>
				</div>
			</div>
		{:else}
			<form class="mt-4 space-y-4" onsubmit={onSubmit}>
				{#if feedbackState.kind === 'error'}
					<p
						class="border border-ink bg-ground-tint p-3 text-meta font-semibold"
						role="alert"
					>
						{feedbackState.message}
					</p>
				{/if}

				{#if kinds.length > 1}
					<fieldset>
						<legend
							class="axis-label mb-2 block"
						>
							What's going on?
						</legend>
						<div class="flex flex-col gap-1.5">
							{#each kinds as k (k.value)}
								<label class="flex items-center gap-2 text-meta font-semibold">
									<input
										type="radio"
										name="feedback-kind"
										value={k.value}
										checked={selectedKind === k.value}
										onchange={() => (selectedKind = k.value)}
										class="h-4 w-4 accent-accent"
									/>
									{k.label}
								</label>
							{/each}
						</div>
					</fieldset>
				{/if}

				{#if showCategoryPicker}
					<fieldset>
						<legend
							class="axis-label mb-2 block"
						>
							Suggested specialties (optional)
						</legend>
						<div class="grid max-h-40 grid-cols-1 gap-1 overflow-y-auto p-2 sm:grid-cols-2">
							{#each categories as cat (cat.id)}
								<label class="flex items-center gap-1.5 text-coord font-semibold">
									<input
										type="checkbox"
										checked={selectedCategories.includes(cat.id)}
										onchange={(e) =>
											toggleCategory(cat.id, (e.currentTarget as HTMLInputElement).checked)}
										class="h-3.5 w-3.5 accent-accent"
									/>
									{cat.name}
								</label>
							{/each}
						</div>
					</fieldset>
				{/if}

				{#if mode === 'site' && selectedKind === 'company_suggestion'}
					<label class="block">
						<span
							class="axis-label mb-2 block"
						>
							Company name *
						</span>
						<input
							required
							maxlength="200"
							bind:value={companyName}
							class="field"
						/>
					</label>
					<label class="block">
						<span
							class="axis-label mb-2 block"
						>
							Company URL
						</span>
						<input
							type="url"
							maxlength="1000"
							bind:value={companyUrl}
							placeholder="https://…"
							class="field coord"
						/>
					</label>
				{/if}

				<label class="block">
					<span class="axis-label mb-2 block">
						Comment {mode === 'site' && selectedKind === 'general' ? '*' : '(optional)'}
					</span>
					<textarea
						rows="4"
						maxlength={mode === 'job' ? 2000 : 4000}
						bind:value={comment}
						class="field"
						placeholder="Tell us more…"
					></textarea>
				</label>

				<label class="block">
					<span class="axis-label mb-2 block">
						Email (optional)
					</span>
					<input
						type="email"
						maxlength="320"
						bind:value={email}
						class="field"
						autocomplete="email"
						placeholder="If you'd like a reply"
					/>
				</label>

				<div class="flex justify-end gap-2 border-t border-rule pt-4">
					<button type="button" class="btn btn-quiet" onclick={requestClose}>Cancel</button>
					<button type="submit" disabled={!canSubmit} class="btn btn-primary">
						{feedbackState.kind === 'submitting' ? 'Sending…' : 'Send'}
					</button>
				</div>
			</form>
		{/if}
	</div>
</dialog>

<style>
	dialog::backdrop {
		backdrop-filter: blur(1px);
	}
</style>
