<script lang="ts">
	import Wip from '$lib/components/Wip.svelte';

	let { params }: { params: { slug: string } } = $props();
	const name = $derived(params.slug.replaceAll('-', ' '));
</script>

<svelte:head>
	<title>{name} | ASoundJob</title>
</svelte:head>

<Wip title={name}>
	<p class="mt-4 font-mono text-xs tracking-wide text-ink-soft">
		Company profiles with open roles arrive when the directory module ships.
	</p>
</Wip>
