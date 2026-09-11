import type { PageServerLoad } from './$types';
import { api, getBlockedCompanies, getCategories, getCountries, getJobs, getOpenApplications, SITE_URL } from '$lib/server/api';
import type { Paginated, Job } from '$lib/types';

const ALLOWED = [
	'q',
	'category',
	'seniority',
	'job_type',
	'location',
	'country',
	'remote',
	'include_unrelated',
	'salary_min',
	'sort',
	'company',
	'ids'
] as const;

const API_PARAM_ALIASES: Record<string, string> = {
	q: 'search'
};

// Filters whose value is a comma-separated set. These arrive two ways: as one
// CSV param from the enhanced form, or as repeated params from the <noscript>
// checkboxes. `get()` would keep only the first and silently drop the rest.
const CSV_PARAMS = new Set(['category', 'seniority', 'job_type']);

export const load: PageServerLoad = async ({ url }) => {
	const params: Record<string, string> = {};
	for (const key of ALLOWED) {
		if (CSV_PARAMS.has(key)) {
			const all = url.searchParams
				.getAll(key)
				.flatMap((v) => v.split(','))
				.map((v) => v.trim())
				.filter(Boolean);
			if (all.length) params[key] = [...new Set(all)].join(',');
		} else {
			const value = url.searchParams.get(key);
			// The salary axis always submits, so it arrives as "0" when untouched.
			// That is not a filter: it would show a "Pays at least: $0" chip and
			// ride along in every shared URL.
			if (value && !(key === 'salary_min' && Number(value) <= 0)) params[key] = value;
		}
	}
	const bookmarked = url.searchParams.get('bookmarked') === 'true';
	const page = Math.max(1, parseInt(url.searchParams.get('page') ?? '1', 10) || 1);
	params['page'] = String(page);
	if (!params.per_page) params.per_page = '20';

	const apiParams: Record<string, string> = {};
	for (const [key, value] of Object.entries(params)) {
		apiParams[API_PARAM_ALIASES[key] ?? key] = value;
	}

	const [jobs, categories, countries, totalResult, openApplications, blocked] =
		await Promise.all([
			getJobs(apiParams).catch(() => null),
			getCategories().catch(() => null),
			getCountries().catch(() => null),
			api<Paginated<Job>>('/api/jobs?per_page=1').catch(() => null),
			getOpenApplications().catch(() => null),
			getBlockedCompanies().catch(() => null)
		]);

	return {
		siteUrl: SITE_URL,
		jobs,
		boardUnavailable: jobs === null,
		categories,
		countries,
		params,
		page,
		bookmarked,
		openApplications,
		blocked,
		totalJobs: totalResult?.total ?? 0
	};
};
