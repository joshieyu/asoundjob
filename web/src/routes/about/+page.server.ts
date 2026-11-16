import type { PageServerLoad } from './$types';
import { getCategories, getCompanies, SITE_URL } from '$lib/server/api';

export const load: PageServerLoad = async () => {
	const [categories, companies] = await Promise.all([
		getCategories().catch(() => null),
		getCompanies({ per_page: '1' }).catch(() => null)
	]);

	return {
		siteUrl: SITE_URL,
		meta: {
			title: 'About | ASoundJob',
			description:
				'ASoundJob is built by Young Audio Professionals — a peer community for people working in audio.'
		},
		categoryCount: categories?.categories.length ?? 0,
		companyCount: companies?.total ?? 0
	};
};
