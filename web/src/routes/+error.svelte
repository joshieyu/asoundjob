<script lang="ts">
	import { page } from '$app/state';

	const detail = $derived(page.error?.message?.trim() ?? '');
</script>

<svelte:head>
	<title>{page.status === 404 ? 'Not found' : `Error ${page.status}`} | ASoundJob</title>
</svelte:head>

<div class="mx-auto mt-16 mb-32 max-w-3xl sm:mt-28">
	<p class="specimen text-muted">{page.status}</p>

	<h1 class="mt-8 text-display font-light tracking-tight text-balance">
		{page.status === 404 ? "We couldn't find that page." : 'Something went wrong.'}
	</h1>

	{#if detail}
		<p class="mt-5 max-w-[68ch] text-body leading-relaxed text-muted">{detail}</p>
	{/if}

	<a href="/" class="btn btn-primary mt-12">Back to the board</a>
</div>
