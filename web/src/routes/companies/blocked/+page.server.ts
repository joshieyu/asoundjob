import type { PageServerLoad } from './$types';
import { getBlockedCompanies, SITE_URL } from '$lib/server/api';

export const load: PageServerLoad = async () => {
	const blocked = await getBlockedCompanies().catch(() => null);

	return {
		siteUrl: SITE_URL, blocked };
};
