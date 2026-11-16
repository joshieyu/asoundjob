import type { PageServerLoad } from './$types';
import { api, getJobs, getCategories, getFeaturedJobs, SITE_URL } from '$lib/server/api';
import type { Paginated, Job } from '$lib/types';

const FRESH_COUNT = 8;

export const load: PageServerLoad = async () => {
	const [categories, totalResult, featuredJobs] = await Promise.all([
		getCategories().catch(() => null),
		api<Paginated<Job>>('/api/jobs?per_page=1').catch(() => null),
		getFeaturedJobs().catch(() => [] as Job[])
	]);

	const featuredIds = new Set(featuredJobs.map((job) => job.id));
	const fetchCount = String(FRESH_COUNT + featuredIds.size);

	const allCategoryIds = (categories?.categories ?? []).map((c) => c.id).join(',');
	const specialtyJobs = allCategoryIds
		? await getJobs({ category: allCategoryIds, per_page: fetchCount, sort: 'newest' }).catch(
				() => null
			)
		: null;

	let candidates = specialtyJobs?.items ?? [];
	let fallbackFailed = false;
	if (candidates.filter((job) => !featuredIds.has(job.id)).length < 4) {
		const fallback = await getJobs({ per_page: fetchCount, sort: 'newest' }).catch(() => null);
		fallbackFailed = fallback === null;
		candidates = [...candidates, ...(fallback?.items ?? [])];
	}

	const seen = new Set<number>(featuredIds);
	const fresh = candidates.filter((job) => !seen.has(job.id) && seen.add(job.id)).slice(0, FRESH_COUNT);

	return {
		siteUrl: SITE_URL,
		boardUnavailable: specialtyJobs === null && fallbackFailed,
		featuredJobs,
		fresh,
		categories,
		totalJobs: totalResult?.total ?? 0,
		meta: {
			title: 'ASoundJob — Audio industry jobs, filtered by specialty',
			description:
				'Job board for audio professionals: DSP, live sound, acoustics, game audio and more. Fresh listings scraped nightly from real audio companies.'
		}
	};
};
