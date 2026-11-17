import type { ParamMatcher } from '@sveltejs/kit';
import { SPECIALTY_BY_SLUG } from '$lib/specialties';

export const match: ParamMatcher = (param) => SPECIALTY_BY_SLUG.has(param);
