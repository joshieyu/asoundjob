<script lang="ts">
	let { days, maxDays = 90 }: { days: number | null; maxDays?: number } = $props();

	const position = $derived(
		days === null ? null : Math.min(100, Math.max(0, (days / maxDays) * 100))
	);
</script>

{#if position !== null}
	<span class="relative block h-px w-full bg-muted/50" aria-hidden="true">
		<span
			class="absolute top-1/2 block h-2 w-px -translate-y-1/2 bg-ink"
			style="left: {position}%"
		></span>
	</span>
{/if}
