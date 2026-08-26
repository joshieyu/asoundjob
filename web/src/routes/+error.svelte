<script lang="ts">
	import { page } from '$app/state';
</script>

<svelte:head>
	<title>{page.status === 404 ? 'Not found' : `Error ${page.status}`} | ASoundJob</title>
</svelte:head>

<div class="panel mx-auto mt-16 max-w-md p-8 text-center">
	<p class="readout text-6xl font-semibold text-fader-deep">{page.status}</p>
	<p class="mt-3 font-mono text-sm tracking-wide text-ink-soft uppercase">
		{page.status === 404 ? 'No signal on this channel' : 'Something clipped the signal'}
	</p>
	<p class="mt-2 text-sm text-ink-soft">{page.error?.message ?? ''}</p>
	<a href="/" class="btn-primary mt-6">Back to the board</a>
</div>
