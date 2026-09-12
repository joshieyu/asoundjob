import type { RequestHandler } from './$types';
import { SITE_URL, api } from '$lib/server/api';
import type { Job, Paginated } from '$lib/types';

interface CompanySlug {
	slug: string;
	created_at: string;
}

const PER_PAGE = 100;
const MAX_JOB_PAGES = 60;
const MAX_COMPANY_PAGES = 30;

export const GET: RequestHandler = async () => {
	const staticRoutes = [
		'',
		'/jobs',
		'/jobs/submit',
		'/companies',
		'/companies/blocked',
		'/resources',
		'/about'
	];

	const jobEntries: string[] = [];
	try {
		for (let page = 1; page <= MAX_JOB_PAGES; page++) {
			const result = await api<Paginated<Job>>(
				`/api/jobs?per_page=${PER_PAGE}&page=${page}&sort=newest`
			);
			for (const job of result.items) {
				const lastmod = (job.posted_date ?? job.scraped_at ?? '').slice(0, 10);
				jobEntries.push(
					`\t<url><loc>${SITE_URL}/jobs/${job.id}</loc>${lastmod ? `<lastmod>${lastmod}</lastmod>` : ''}<priority>0.8</priority></url>`
				);
			}
			if (page >= result.pages) break;
		}
	} catch (err) {
		console.warn('sitemap: job URLs omitted —', err);
	}

	const companyEntries: string[] = [];
	try {
		for (let page = 1; page <= MAX_COMPANY_PAGES; page++) {
			const result = await api<Paginated<CompanySlug>>(
				`/api/companies?per_page=${PER_PAGE}&page=${page}`
			);
			for (const company of result.items) {
				companyEntries.push(
					`\t<url><loc>${SITE_URL}/companies/${company.slug}</loc><priority>0.5</priority></url>`
				);
			}
			if (page >= result.pages) break;
		}
	} catch (err) {
		console.warn('sitemap: company URLs omitted —', err);
	}

	const urls = [
		...staticRoutes.map(
			(route) =>
				`\t<url><loc>${SITE_URL}${route || '/'}</loc><priority>${route === '' ? '1.0' : '0.6'}</priority></url>`
		),
		...jobEntries,
		...companyEntries
	].join('\n');

	const xml = `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls}\n</urlset>\n`;

	return new Response(xml, {
		headers: {
			'Content-Type': 'application/xml',
			'Cache-Control': 'max-age=3600'
		}
	});
};
