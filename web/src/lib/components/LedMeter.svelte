<script lang="ts">
	let { value, max = 200000, label }: { value: number | null; max?: number; label?: string } = $props();

	const SEGMENTS = 12;
	const lit = $derived(
		value && value > 0 ? Math.max(1, Math.min(SEGMENTS, Math.ceil((value / max) * SEGMENTS))) : 0
	);
</script>

<div class="flex h-full w-3 flex-col justify-end gap-[2px]" role="img" aria-label={label ?? 'Salary level'}>
	{#each Array.from({ length: SEGMENTS }, (_, i) => i) as seg (seg)}
		{@const isLit = SEGMENTS - seg <= lit}
		{@const position = SEGMENTS - seg}
		<span
			class="flex-1 rounded-[1px] transition-colors duration-300"
			class:bg-lit={isLit}
			style={isLit
				? position > SEGMENTS - 2
					? 'background:#c45447'
					: position > SEGMENTS - 5
						? 'background:#d9a13b'
						: undefined
				: undefined}
			class:bg-led-0={!isLit}
		></span>
	{/each}
</div>
