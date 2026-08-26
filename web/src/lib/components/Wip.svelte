<script lang="ts">
	import type { Snippet } from 'svelte';

	let { title, children }: { title: string; children?: Snippet } = $props();
</script>

<div class="panel mx-auto mt-10 max-w-2xl p-8 text-center">
	<p class="legend !justify-center">MODULE PENDING — WORK IN PROGRESS</p>
	<h1 class="mt-4 text-3xl font-black tracking-tight">{title}</h1>
	<p class="mx-auto mt-3 max-w-md text-sm leading-relaxed text-ink-soft">
		This section of ASoundJob is under construction. We're building it in the open
		with the Young Audio Professionals community — it ships soon.
	</p>
	{#if children}
		{@render children()}
	{/if}
	<a href="/jobs" class="btn-primary mt-6">Browse jobs meanwhile</a>
</div>
