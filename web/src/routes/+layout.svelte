<script lang="ts">
	import '../app.css';
	import '@fontsource-variable/archivo';
	import '@fontsource-variable/spline-sans-mono';
	import Header from '$lib/components/Header.svelte';
	import Footer from '$lib/components/Footer.svelte';

	let { children } = $props();
</script>

<Header />
<main id="main" class="mx-auto w-full max-w-6xl flex-1 px-4 pb-16 pt-6 sm:px-6">
	{@render children()}
</main>
<Footer />
