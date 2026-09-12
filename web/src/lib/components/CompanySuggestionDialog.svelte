<script lang="ts">
	import { submitCompanySuggestion, type FeedbackState } from '$lib/feedback';

	let {
		slug,
		companyName,
		open = $bindable(false)
	}: {
		slug: string;
		companyName: string;
		open?: boolean;
	} = $props();

	let dialogEl: HTMLDialogElement | undefined = $state();
	let description = $state('');
	let headquarters = $state('');
	let founded: number | undefined = $state(undefined);
	let links = $state<{ label: string; url: string }[]>([{ label: '', url: '' }]);
	let comment = $state('');
	let email = $state('');
	let feedbackState = $state<FeedbackState>({ kind: 'idle' });

	$effect(() => {
		if (!dialogEl) return;
		if (open && !dialogEl.open) {
			description = '';
			headquarters = '';
			founded = undefined;
			links = [{ label: '', url: '' }];
			comment = '';
			email = '';
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

	function addLink() {
		if (links.length < 5) links = [...links, { label: '', url: '' }];
	}

	function removeLink(index: number) {
		links = links.filter((_, i) => i !== index);
	}

	const completeLinks = $derived(
		links.filter((l) => l.label.trim().length > 0 && l.url.trim().length > 0)
	);

	const canSubmit = $derived.by(() => {
		if (feedbackState.kind === 'submitting') return false;
		return (
			description.trim().length > 0 ||
			headquarters.trim().length > 0 ||
			founded !== undefined ||
			completeLinks.length > 0
		);
	});

	async function onSubmit(event: SubmitEvent) {
		event.preventDefault();
		if (!canSubmit) return;
		feedbackState = { kind: 'submitting' };
		feedbackState = await submitCompanySuggestion(slug, {
			description: description.trim() || null,
			links:
				completeLinks.length > 0
					? completeLinks.map((l) => ({ label: l.label.trim(), url: l.url.trim() }))
					: null,
			headquarters: headquarters.trim() || null,
			founded: founded ?? null,
			comment: comment.trim() || null,
			submitter_email: email.trim() || null
		});
	}
</script>

<dialog
	bind:this={dialogEl}
	onclose={requestClose}
	onclick={onBackdropClick}
	class="m-auto w-[min(92vw,32rem)] border-rule p-0 backdrop:bg-ink/40"
	aria-labelledby="company-suggestion-dialog-title"
>
	<div class="p-5 sm:p-6">
		<div class="flex items-start justify-between gap-3">
			<div class="min-w-0">
				<h2 id="company-suggestion-dialog-title" class="mt-1 truncate text-title font-bold">
					Suggest an edit for {companyName}
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
				<p class="mt-2 text-meta text-muted">
					A moderator reviews suggestions before they go live on the company page.
				</p>
				<div class="mt-4 flex justify-end">
					<button type="button" class="btn btn-primary" onclick={requestClose}>Done</button>
				</div>
			</div>
		{:else}
			<form class="mt-4 space-y-4" onsubmit={onSubmit}>
				{#if feedbackState.kind === 'error'}
					<p class="border border-ink bg-ground-tint p-3 text-meta font-semibold" role="alert">
						{feedbackState.message}
					</p>
				{/if}

				<label class="block">
					<span class="axis-label mb-2 block">Description</span>
					<textarea
						rows="4"
						maxlength="2000"
						bind:value={description}
						class="field"
						placeholder="What does {companyName} do?"
					></textarea>
				</label>

				<label class="block">
					<span class="axis-label mb-2 block">Headquarters</span>
					<input maxlength="200" bind:value={headquarters} class="field" placeholder="City, country" />
				</label>

				<label class="block">
					<span class="axis-label mb-2 block">Founded</span>
					<input
						type="number"
						min="1800"
						max="2100"
						bind:value={founded}
						class="field coord"
						placeholder="Year"
					/>
				</label>

				<fieldset>
					<legend class="axis-label mb-2 block">Reference links (optional)</legend>
					<div class="flex flex-col gap-3">
						{#each links as link, i (i)}
							<div class="border border-rule p-3">
								<div class="flex items-center justify-between gap-2">
									<span class="axis-label">Link {i + 1}</span>
									{#if links.length > 1}
										<button
											type="button"
											class="coord font-semibold text-muted hover:text-accent"
											onclick={() => removeLink(i)}
										>
											Remove
										</button>
									{/if}
								</div>
								<label class="mt-2 block">
									<span class="axis-label mb-1 block">Label</span>
									<input maxlength="80" bind:value={links[i].label} class="field" placeholder="Wikipedia" />
								</label>
								<label class="mt-2 block">
									<span class="axis-label mb-1 block">URL</span>
									<input
										type="url"
										maxlength="1000"
										bind:value={links[i].url}
										class="field coord"
										placeholder="https://…"
									/>
								</label>
							</div>
						{/each}
					</div>
					{#if links.length < 5}
						<button type="button" class="btn btn-quiet mt-3" onclick={addLink}>
							Add another link
						</button>
					{/if}
				</fieldset>

				<label class="block">
					<span class="axis-label mb-2 block">Comment (optional)</span>
					<textarea
						rows="3"
						maxlength="2000"
						bind:value={comment}
						class="field"
						placeholder="Anything else we should know?"
					></textarea>
				</label>

				<label class="block">
					<span class="axis-label mb-2 block">Email (optional)</span>
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
