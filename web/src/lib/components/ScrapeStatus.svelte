<script lang="ts">
	import type { CompanyRecord } from '$lib/types';
	import { timeAgo } from '$lib/format';

	let {
		company,
		compact = false
	}: {
		company: Pick<CompanyRecord, 'scrape_status' | 'last_scraped_at' | 'consecutive_failures'>;
		compact?: boolean;
	} = $props();

	const failures = $derived(company.consecutive_failures);
	const label = $derived(
		company.scrape_status === 'tracked'
			? compact
				? 'tracked'
				: `Jobs tracked automatically · checked ${timeAgo(company.last_scraped_at)}`
			: company.scrape_status === 'failing'
				? compact
					? 'check failing'
					: `We couldn't read the careers page on the last ${failures === 1 ? 'check' : `${failures} checks`}`
				: compact
					? 'not tracked'
					: 'Jobs not tracked automatically'
	);
	const title = $derived(
		company.scrape_status === 'tracked'
			? 'The careers page was read successfully on the last scrape'
			: company.scrape_status === 'failing'
				? 'Recent scrapes could not read the careers page, so listings may be out of date'
				: 'We do not scrape this company yet; check its careers page directly'
	);
</script>

<span class="inline-flex items-center gap-1.5 {compact ? 'coord' : 'text-meta'} text-muted" {title}>
	{#if company.scrape_status === 'tracked'}
		<span class="inline-block h-2 w-2 shrink-0 rounded-full bg-accent" aria-hidden="true"></span>
	{:else if company.scrape_status === 'failing'}
		<span class="inline-block h-2 w-2 shrink-0 rounded-full border border-accent" aria-hidden="true"></span>
	{:else}
		<span class="inline-block h-2 w-2 shrink-0 rounded-full border border-muted" aria-hidden="true"></span>
	{/if}
	<span>{label}</span>
</span>
