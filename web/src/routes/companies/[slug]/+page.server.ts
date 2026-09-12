import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
import { getCompany, SITE_URL, ApiError } from '$lib/server/api';

export const load: PageServerLoad = async ({ params }) => {
	let company;
	try {
		company = await getCompany(params.slug);
	} catch (err) {
		if (err instanceof ApiError && err.status === 404) error(404, 'Company not found');
		throw err;
	}

	return {
		siteUrl: SITE_URL,
		company,
		meta: {
			title: `${company.name} | ASoundJob`,
			description: (
				company.description ?? `${company.name} on ASoundJob — open roles and company details.`
			).slice(0, 158)
		}
	};
};
