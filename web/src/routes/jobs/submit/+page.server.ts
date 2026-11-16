import type { PageServerLoad } from './$types';
import { getCategories, SITE_URL } from '$lib/server/api';

export const load: PageServerLoad = async () => {
	const categories = await getCategories().catch(() => ({ categories: [] }));
	return {
		categories,
		siteUrl: SITE_URL,
		meta: {
			title: 'Submit a job | ASoundJob',
			description:
				'Submit an audio industry job to ASoundJob. Free, reviewed by moderators, live within days.'
		}
	};
};
