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
		<div class="flex items-center gap-1">
			{#if data.page > 1}
				<a href={makeHref(1)} aria-label="First page" title="First page" class="btn btn-quiet !px-2 sm:!px-3"><svg width="12" height="12" viewBox="0 0 16 16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v10M13 4L9 8l4 4"/></svg><span class="hidden sm:inline">First</span></a>
				<a href={makeHref(data.page - 1)} rel="prev" aria-label="Previous page" class="btn btn-quiet !px-2 sm:!px-3"><svg width="12" height="12" viewBox="0 0 16 16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M13 8H3M7 4L3 8l4 4"/></svg><span class="hidden sm:inline">Prev</span></a>
			{/if}
		</div>

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

		<div class="flex items-center gap-1">
			{#if data.page < data.pages}
				<a href={makeHref(data.page + 1)} rel="next" aria-label="Next page" class="btn btn-quiet !px-2 sm:!px-3"><span class="hidden sm:inline">Next</span><svg width="12" height="12" viewBox="0 0 16 16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M3 8h10M9 4l4 4-4 4"/></svg></a>
				<a href={makeHref(data.pages)} aria-label="Last page, {data.pages}" title="Last page" class="btn btn-quiet !px-2 sm:!px-3"><span class="hidden sm:inline">Last</span><svg width="12" height="12" viewBox="0 0 16 16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M13 3v10M3 4l4 4-4 4"/></svg></a>
			{/if}
		</div>
	</nav>
{/if}
