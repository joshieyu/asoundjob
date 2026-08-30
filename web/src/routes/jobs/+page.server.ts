import type { PageServerLoad } from './$types';
import { api, getCategories, getCompanies, getCountries, getJobs } from '$lib/server/api';
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
	'salary_max',
	'sort',
	'company_id'
] as const;

export const load: PageServerLoad = async ({ url }) => {
	const params: Record<string, string> = {};
	for (const key of ALLOWED) {
		const value = url.searchParams.get(key);
		if (value) params[key] = value;
	}
	const page = Math.max(1, parseInt(url.searchParams.get('page') ?? '1', 10) || 1);
	params['page'] = String(page);
	if (!params.per_page) params.per_page = '20';

	const [jobs, categories, companies, countries, totalResult] = await Promise.all([
		getJobs(params).catch(() => null),
		getCategories().catch(() => null),
		getCompanies({ verified_only: 'true', per_page: '100' }).catch(() => null),
		getCountries().catch(() => null),
		api<Paginated<Job>>('/api/jobs?per_page=1').catch(() => null)
	]);

	return {
		jobs,
		categories,
		companies,
		countries,
		params,
		page,
		totalJobs: totalResult?.total ?? 0
	};
};
