import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
import { getJob, getCategories, SITE_URL } from '$lib/server/api';
import { renderDescription } from '$lib/sanitize';
import type { Job } from '$lib/types';

const EMPLOYMENT_TYPES: Record<string, string> = {
	'full-time': 'FULL_TIME',
	'part-time': 'PART_TIME',
	contract: 'CONTRACTOR',
	temporary: 'TEMPORARY',
	internship: 'INTERN',
	volunteer: 'VOLUNTEER'
};

function jobPosting(job: Job, description: string) {
	const company = job.company;
	return {
		'@context': 'https://schema.org',
		'@type': 'JobPosting',
		title: job.title,
		description,
		identifier: { '@type': 'PropertyValue', name: 'ASoundJob', value: String(job.id) },
		datePosted: job.posted_date ?? job.created_at.slice(0, 10),
		validThrough: job.expires_date ?? undefined,
		employmentType: (job.job_type && EMPLOYMENT_TYPES[job.job_type]) || undefined,
		directApply: false,
		hiringOrganization: company
			? {
					'@type': 'Organization',
					name: company.name,
					sameAs: company.website_url ?? undefined,
					logo: company.logo_url ?? undefined
				}
			: undefined,
		jobLocation:
			job.location || job.country
				? {
						'@type': 'Place',
						address: {
							'@type': 'PostalAddress',
							addressLocality: job.location ?? undefined,
							addressCountry: job.country ?? undefined
						}
					}
				: undefined,
		jobLocationType: job.remote ? 'TELECOMMUTE' : undefined,
		applicantLocationRequirements:
			job.remote && job.country
				? { '@type': 'Country', name: job.country_name ?? job.country }
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
		url: `${SITE_URL}/jobs/${job.id}`
	};
}

export const load: PageServerLoad = async ({ params }) => {
	const [job, categories] = await Promise.all([
		getJob(Number(params.id)).catch(() => null),
		getCategories().catch(() => ({ categories: [] }))
	]);
	if (!job) error(404, 'Job not found');

	const rawDescription = job.description ?? '';
	const { html: description, plain: plainDescription } = renderDescription(rawDescription);

	const open = job.is_active;
	const jsonLd = open ? jobPosting(job, description ?? `<p>${plainDescription}</p>`) : null;

	return {
		siteUrl: SITE_URL,
		job,
		description,
		plainDescription,
		jsonLd,
		indexable: open,
		categories: categories.categories,
		meta: {
			title: `${job.title} at ${job.company?.name ?? 'Unknown company'} | ASoundJob`,
			description: plainDescription.slice(0, 158)
		}
	};
};
