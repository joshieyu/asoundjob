import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
import { getJob, getCategories, SITE_URL } from '$lib/server/api';
import { renderDescription } from '$lib/sanitize';

export const load: PageServerLoad = async ({ params }) => {
	const [job, categories] = await Promise.all([
		getJob(Number(params.id)).catch(() => null),
		getCategories().catch(() => ({ categories: [] }))
	]);
	if (!job) error(404, 'Job not found');

	const rawDescription = job.description ?? '';
	const { html: description, plain: plainDescription } = renderDescription(rawDescription);

	const jsonLd = {
		'@context': 'https://schema.org',
		'@type': 'JobPosting',
		title: job.title,
		description: description ?? `<p>${plainDescription}</p>`,
		datePosted: job.posted_date ?? undefined,
		employmentType: job.job_type?.toUpperCase().replace('-', '_') || undefined,
		hiringOrganization: job.company
			? {
					'@type': 'Organization',
					name: job.company.name,
					sameAs: `${SITE_URL}/companies/${job.company.slug}`
				}
			: undefined,
		jobLocationType: job.remote ? 'TELECOMMUTE' : undefined,
		jobLocation: job.location && !job.remote
			? {
					'@type': 'Place',
					address: { '@type': 'PostalAddress', addressLocality: job.location }
				}
			: undefined,
		baseSalary:
			job.salary_min || job.salary_max
				? {
						'@type': 'MonetaryAmount',
						currency: job.salary_currency ?? 'USD',
						value: {
							'@type': 'QuantitativeValue',
							minValue: job.salary_min ?? undefined,
							maxValue: job.salary_max ?? undefined,
							unitText: 'YEAR'
						}
					}
				: undefined,
		url: `${SITE_URL}/jobs/${job.id}`,
		validThrough: job.expires_date ?? undefined
	};

	return {
		job,
		description,
		plainDescription,
		jsonLd,
		categories: categories.categories,
		meta: {
			title: `${job.title} at ${job.company?.name ?? 'Unknown company'} | ASoundJob`,
			description: plainDescription.slice(0, 158)
		}
	};
};
