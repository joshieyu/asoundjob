<script lang="ts">
	import Wip from '$lib/components/Wip.svelte';

	let { params }: { params: { slug: string } } = $props();

	const MAX_NAME_LENGTH = 60;

	const name = $derived.by(() => {
		const words = params.slug.replaceAll('-', ' ').replace(/\s+/g, ' ').trim();
		if (!words) return 'This company';
		const clipped =
			words.length > MAX_NAME_LENGTH
				? words.slice(0, MAX_NAME_LENGTH).trimEnd() + '…'
				: words;
		return clipped.replace(/(^|\s)(\p{Ll})/gu, (_, gap, letter) => gap + letter.toUpperCase());
	});
</script>

<svelte:head>
	<title>{name} | ASoundJob</title>
</svelte:head>

<Wip title={name}>
	<p class="mt-6 max-w-[68ch] text-body leading-relaxed text-muted">
		Company profiles with open roles arrive when the directory module ships.
	</p>
</Wip>
