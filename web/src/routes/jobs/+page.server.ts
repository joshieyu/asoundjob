import type { PageServerLoad } from './$types';
import { loadBoard } from '$lib/server/board';

export const load: PageServerLoad = async ({ url }) => loadBoard(url);
