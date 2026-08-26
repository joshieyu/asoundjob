import type { PageServerLoad } from './$types';
import { api, getJobs, getCategories } from '$lib/server/api';
import type { Paginated, Job } from '$lib/types';

const ALL_CATEGORY_IDS = [
	'audio_dsp',
	'audio_software',
	'audio_ee',
	'transducers_microphones',
	'acoustics_architectural',
	'live_sound_events',
	'music_technology',
	'audio_systems',
	'automotive_audio',
	'audio_aiml',
	'nvh',
	'psychoacoustics_perception',
	'game_audio_interactive',
	'music_production_recording'
].join(',');

export const load: PageServerLoad = async ({ fetch }) => {
	const [specialtyJobs, categories, totalResult] = await Promise.all([
		getJobs({ category: ALL_CATEGORY_IDS, per_page: '8', sort: 'newest' }).catch(() => null),
		getCategories().catch(() => null),
		api<Paginated<Job>>('/api/jobs?per_page=1').catch(() => null)
	]);

	let featured = specialtyJobs;
	if (!featured || featured.items.length < 4) {
		const fallback = await getJobs({ per_page: '8', sort: 'newest' }).catch(() => null);
		const merged = [...(featured?.items ?? []), ...(fallback?.items ?? [])];
		const seen = new Set<number>();
		featured = {
			items: merged.filter((job) => !seen.has(job.id) && seen.add(job.id)).slice(0, 8),
			total: fallback?.total ?? featured?.total ?? 0,
			page: 1,
			per_page: 8,
			pages: 1
		};
	}

	return {
		featured,
		categories,
		totalJobs: totalResult?.total ?? 0,
		meta: {
			title: 'ASoundJob — Audio industry jobs, filtered by specialty',
			description:
				'Job board for audio professionals: DSP, live sound, acoustics, game audio and more. Fresh listings scraped nightly from real audio companies.'
		}
	};
};
