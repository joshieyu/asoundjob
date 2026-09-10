<script lang="ts">
	import type { Snippet } from 'svelte';

	let {
		label,
		title,
		count = null,
		open = false,
		children
	}: {
		label: string;
		title: string;
		count?: number | null;
		open?: boolean;
		children: Snippet;
	} = $props();
</script>

<details class="panel group" {open}>
	<summary
		class="flex cursor-pointer list-none items-center gap-3 rounded-md p-4 transition-colors hover:bg-panel-recessed/40 [&::-webkit-details-marker]:hidden"
	>
		<span class="font-mono text-[10px] tracking-[0.14em] text-ink-soft uppercase">{label}</span>
		<span class="text-sm font-bold text-balance">{title}</span>
		{#if count !== null}
			<span class="rounded-sm border border-seam bg-panel-recessed px-1 font-mono text-[10px]">
				{count}
			</span>
		{/if}
		<svg
			class="ml-auto h-4 w-4 shrink-0 text-ink-soft transition-transform group-open:rotate-180"
			viewBox="0 0 16 16"
			fill="none"
			stroke="currentColor"
			stroke-width="1.5"
			aria-hidden="true"
		>
			<path d="M4 6l4 4 4-4" stroke-linecap="round" stroke-linejoin="round" />
		</svg>
	</summary>
	<div class="border-t border-seam p-4">
		{@render children()}
	</div>
</details>
