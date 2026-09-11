<script lang="ts">
	import type { Snippet } from 'svelte';

	let {
		title,
		count = null,
		open = false,
		children
	}: {
		title: string;
		count?: number | null;
		open?: boolean;
		children: Snippet;
	} = $props();
</script>

<details class="group" {open}>
	<summary
		class="flex cursor-pointer list-none items-center gap-3 p-4 transition-colors hover:bg-ground-tint/40 [&::-webkit-details-marker]:hidden"
	>
		<span class="text-meta font-bold text-balance">{title}</span>
		{#if count !== null}
			<span class="border border-rule bg-ground-tint px-1 coord">
				{count}
			</span>
		{/if}
		<svg
			class="ml-auto h-4 w-4 shrink-0 text-muted transition-transform group-open:rotate-180"
			viewBox="0 0 16 16"
			fill="none"
			stroke="currentColor"
			stroke-width="1.5"
			aria-hidden="true"
		>
			<path d="M4 6l4 4 4-4" stroke-linecap="round" stroke-linejoin="round" />
		</svg>
	</summary>
	<div class="border-t border-rule p-4">
		{@render children()}
	</div>
</details>
