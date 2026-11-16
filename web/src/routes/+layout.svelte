<script lang="ts">
	import '../app.css';
	import '@fontsource-variable/recursive/mono.css';
	import Header from '$lib/components/Header.svelte';
	import Footer from '$lib/components/Footer.svelte';
	import { page } from '$app/state';

	let { children } = $props();

	const meta = $derived(page.data.meta as { title: string; description: string } | undefined);
	const siteUrl = $derived(page.data.siteUrl as string | undefined);
	const shareTitle = $derived(meta?.title.replace(/ \| ASoundJob$/, '') ?? '');
</script>

<svelte:head>
	<meta property="og:site_name" content="ASoundJob" />
	<meta property="og:type" content="website" />
	<meta name="twitter:card" content="summary" />
	{#if meta}
		<meta property="og:title" content={shareTitle} />
		<meta property="og:description" content={meta.description} />
		<meta name="twitter:title" content={shareTitle} />
		<meta name="twitter:description" content={meta.description} />
	{/if}
	{#if siteUrl}
		<meta property="og:url" content="{siteUrl}{page.url.pathname}" />
		<meta property="og:image" content="{siteUrl}/favicon-180.png" />
	{/if}
</svelte:head>

<Header />
<main id="main" class="mx-auto w-full max-w-6xl flex-1 px-4 pb-16 pt-6 sm:px-6">
	{@render children()}
</main>
<Footer />
