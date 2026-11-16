import type { RequestHandler } from './$types';
import { SITE_URL } from '$lib/server/api';

export const GET: RequestHandler = () =>
	new Response(`User-agent: *\nAllow: /\nDisallow: /admin\n\nSitemap: ${SITE_URL}/sitemap.xml\n`, {
		headers: { 'Content-Type': 'text/plain; charset=utf-8', 'Cache-Control': 'max-age=3600' }
	});
