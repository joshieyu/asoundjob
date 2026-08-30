import type { PageServerLoad } from './$types';
import { getCategories, getCompanies } from '$lib/server/api';

export const load: PageServerLoad = async () => {
	const [categories, companies] = await Promise.all([
		getCategories().catch(() => null),
		getCompanies({ per_page: '1' }).catch(() => null)
	]);

	return {
		categoryCount: categories?.categories.length ?? 0,
		companyCount: companies?.total ?? 0
	};
};
