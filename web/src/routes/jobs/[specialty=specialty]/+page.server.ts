import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
import { loadBoard } from '$lib/server/board';
import { SPECIALTY_BY_SLUG } from '$lib/specialties';

export const load: PageServerLoad = async ({ url, params }) => {
	const specialty = SPECIALTY_BY_SLUG.get(params.specialty);
	if (!specialty) error(404, 'Not found');
	return loadBoard(url, specialty);
};
