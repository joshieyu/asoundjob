<script lang="ts">
	import type { Paginated } from '$lib/types';

	let { data, makeHref }: { data: Paginated<unknown>; makeHref: (page: number) => string } =
		$props();

	type Item = { kind: 'page'; page: number } | { kind: 'gap'; key: string };

	const items = $derived.by(() => {
		const total = data.pages;
		const current = data.page;
		const shown = [...new Set([1, current - 1, current, current + 1, total])]
			.filter((p) => p >= 1 && p <= total)
			.sort((a, b) => a - b);
		const out: Item[] = [];
		shown.forEach((p, i) => {
			const prev = shown[i - 1];
			if (prev !== undefined && p - prev === 2) out.push({ kind: 'page', page: prev + 1 });
			else if (prev !== undefined && p - prev > 2) out.push({ kind: 'gap', key: `gap-${prev}` });
			out.push({ kind: 'page', page: p });
		});
		return out;
	});

	function rel(p: number): string | undefined {
		if (p === data.page - 1) return 'prev';
		if (p === data.page + 1) return 'next';
		return undefined;
	}
</script>

{#if data.pages > 1}
	<nav aria-label="Pagination" class="mt-6 flex justify-center">
		<ol class="coord flex flex-wrap items-center justify-center gap-1">
			{#each items as item (item.kind === 'page' ? item.page : item.key)}
				<li>
					{#if item.kind === 'gap'}
						<span class="flex h-8 min-w-6 items-end justify-center pb-1.5 text-muted" aria-hidden="true">…</span>
					{:else}
						<a
							href={makeHref(item.page)}
							rel={rel(item.page)}
							aria-current={item.page === data.page ? 'page' : undefined}
							aria-label={item.page === data.pages && item.page !== 1
								? `Page ${item.page}, last page`
								: `Page ${item.page}`}
							class="flex h-8 min-w-8 items-center justify-center border px-2 transition-colors {item.page ===
							data.page
								? 'border-ink bg-ink text-ground'
								: 'border-rule bg-ground hover:border-accent'}"
						>
							{item.page}
						</a>
					{/if}
				</li>
			{/each}
		</ol>
	</nav>
{/if}
