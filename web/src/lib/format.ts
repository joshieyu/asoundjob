export function formatSalary(min: number | null, max: number | null, currency: string | null): string {
	const symbol = currency === 'USD' ? '$' : currency === 'EUR' ? '€' : currency === 'GBP' ? '£' : '';
	const fmt = (value: number) =>
		value >= 1000 ? `${symbol}${Math.round(value / 1000)}k` : `${symbol}${value}`;
	if (min && max) return `${fmt(min)}–${fmt(max)}`;
	if (min) return `${fmt(min)}+`;
	if (max) return `up to ${fmt(max)}`;
	return '';
}

export function timeAgo(dateStr: string | null): string {
	if (!dateStr) return 'recent';
	const then = new Date(dateStr).getTime();
	if (Number.isNaN(then)) return 'recent';
	const days = Math.floor((Date.now() - then) / 86_400_000);
	if (days <= 0) return 'today';
	if (days === 1) return '1 day ago';
	if (days < 30) return `${days} days ago`;
	const months = Math.floor(days / 30);
	return months === 1 ? '1 month ago' : `${months} months ago`;
}

export function formatDate(dateStr: string | null): string {
	if (!dateStr) return '—';
	const d = new Date(dateStr);
	if (Number.isNaN(d.getTime())) return '—';
	return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
}
