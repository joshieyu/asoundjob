import type { PageServerLoad } from './$types';
import { getBlockedCompanies } from '$lib/server/api';

export const load: PageServerLoad = async () => {
	const blocked = await getBlockedCompanies().catch(() => null);

	return { blocked };
};
