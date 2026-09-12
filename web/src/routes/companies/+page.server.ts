import type { PageServerLoad } from './$types';
import { getCompanies, getCompanyCategories, SITE_URL } from '$lib/server/api';

const SORT_MAP: Record<string, [string, string]> = {
	'board-desc': ['board', 'desc'],
	'name-asc': ['name', 'asc']
};

const DEFAULT_SORT = 'board-desc';

export const load: PageServerLoad = async ({ url }) => {
	const params: Record<string, string> = {};

	const q = url.searchParams.get('q');
	if (q) params.q = q;

	const category = url.searchParams.get('category');
	if (category) params.category = category;

	const hiringOnly = url.searchParams.get('hiring_only');
	if (hiringOnly === 'true') params.hiring_only = 'true';

	const sortParam = url.searchParams.get('sort');
	params.sort = sortParam && SORT_MAP[sortParam] ? sortParam : DEFAULT_SORT;

	const page = Math.max(1, parseInt(url.searchParams.get('page') ?? '1', 10) || 1);
	params.page = String(page);

	const [sort, direction] = SORT_MAP[params.sort];

	const apiParams: Record<string, string> = {
		page: params.page,
		per_page: '24',
		sort,
		direction
	};
	if (params.q) apiParams.search = params.q;
	if (params.category) apiParams.category = params.category;
	if (params.hiring_only) apiParams.hiring_only = 'true';

	const [companies, categories] = await Promise.all([
		getCompanies(apiParams).catch(() => null),
		getCompanyCategories().catch(() => null)
	]);

	return {
		siteUrl: SITE_URL,
		companies,
		boardUnavailable: companies === null,
		categories,
		params,
		page
	};
};
