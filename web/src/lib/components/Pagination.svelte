<script lang="ts">
	import type { Paginated } from '$lib/types';

	let { data, makeHref }: { data: Paginated<unknown>; makeHref: (page: number) => string } =
		$props();

	const pages = $derived.by(() => {
		const total = data.pages;
		const current = data.page;
		const window: number[] = [];
		for (
			let p = Math.max(1, current - 2);
			p <= Math.min(total, current + 2);
			p++
		) {
			window.push(p);
		}
		return window;
	});
</script>

{#if data.pages > 1}
	<nav aria-label="Pagination" class="mt-6 flex items-center justify-between gap-2">
		{#if data.page > 1}
			<a href={makeHref(data.page - 1)} rel="prev" class="btn-latch">← Prev</a>
		{:else}
			<span></span>
		{/if}

		<div class="flex items-center gap-1 font-mono text-sm">
			{#each pages as p (p)}
				<a
					href={makeHref(p)}
					aria-current={p === data.page ? 'page' : undefined}
					aria-label="Page {p}"
					class="flex h-8 min-w-8 items-center justify-center rounded border px-2 transition-colors {p ===
					data.page
						? 'border-fader-deep bg-fader text-white'
						: 'border-seam bg-panel-raised hover:border-fader'}"
				>
					{p}
				</a>
			{/each}
		</div>

		{#if data.page < data.pages}
			<a href={makeHref(data.page + 1)} rel="next" class="btn-latch">Next →</a>
		{:else}
			<span></span>
		{/if}
	</nav>
{/if}
