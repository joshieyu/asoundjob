<script lang="ts">
	import { themeState, startTheme } from '$lib/theme.svelte';

	$effect(() => {
		startTheme();
	});

	const dark = $derived(themeState.current === 'dark');
</script>

<button
	type="button"
	class="js-only flex h-8 w-8 shrink-0 items-center justify-center border border-transparent text-muted transition-colors hover:border-muted hover:text-ink"
	aria-pressed={dark}
	aria-label={dark ? 'Switch to the light board' : 'Switch to the dark board'}
	title={dark ? 'Switch to the light board' : 'Switch to the dark board'}
	onclick={() => themeState.toggle()}
>
	<!-- Half-filled disc: the tone axis at its two ends. Not a sun, not a moon. -->
	<svg width="15" height="15" viewBox="0 0 16 16" aria-hidden="true">
		<circle cx="8" cy="8" r="6.25" fill="none" stroke="currentColor" stroke-width="1.3" />
		<path d="M8 1.75a6.25 6.25 0 0 1 0 12.5Z" fill="currentColor" />
	</svg>
</button>
