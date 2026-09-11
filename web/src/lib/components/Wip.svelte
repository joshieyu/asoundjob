<script lang="ts">
	import type { Snippet } from 'svelte';

	let { title, children }: { title: string; children?: Snippet } = $props();
</script>

<div class="mx-auto mt-16 mb-24 max-w-3xl sm:mt-24">
	<h1 class="text-display font-light tracking-tight text-balance">{title}</h1>

	<p class="mt-8 max-w-[68ch] text-title leading-snug font-light">
		This section of ASoundJob is under construction. We're building it in the open
		with the Young Audio Professionals community — it ships soon.
	</p>

	{#if children}
		{@render children()}
	{/if}

	<a href="/jobs" class="btn btn-primary mt-12">Browse jobs meanwhile</a>
</div>
