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
			<a href={makeHref(data.page - 1)} rel="prev" class="btn btn-quiet"><svg width="12" height="12" viewBox="0 0 16 16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M13 8H3M7 4L3 8l4 4"/></svg>Prev</a>
		{:else}
			<span></span>
		{/if}

		<div class="flex items-center gap-1 coord">
			{#each pages as p (p)}
				<a
					href={makeHref(p)}
					aria-current={p === data.page ? 'page' : undefined}
					aria-label="Page {p}"
					class="flex h-8 min-w-8 items-center justify-center border px-2 transition-colors {p ===
					data.page
						? 'border-ink bg-ink text-ground'
						: 'border-rule bg-ground hover:border-accent'}"
				>
					{p}
				</a>
			{/each}
		</div>

		{#if data.page < data.pages}
			<a href={makeHref(data.page + 1)} rel="next" class="btn btn-quiet">Next<svg width="12" height="12" viewBox="0 0 16 16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M3 8h10M9 4l4 4-4 4"/></svg></a>
		{:else}
			<span></span>
		{/if}
	</nav>
{/if}
