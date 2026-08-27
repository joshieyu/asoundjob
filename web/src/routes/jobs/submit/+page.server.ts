import type { PageServerLoad } from './$types';
import { getCategories } from '$lib/server/api';

export const load: PageServerLoad = async () => {
	const categories = await getCategories().catch(() => ({ categories: [] }));
	return { categories };
};
