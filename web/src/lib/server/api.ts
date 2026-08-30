import { env } from '$env/dynamic/private';
import type {
	CategoryInfo,
	CountriesResponse,
	Job,
	Paginated,
	CompanyRecord
} from '$lib/types';

const API_URL = env.API_URL ?? 'http://127.0.0.1:8000';

export class ApiError extends Error {
	status: number;
	constructor(status: number, message: string) {
		super(message);
		this.status = status;
	}
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
	let response: Response;
	try {
		response = await fetch(`${API_URL}${path}`, init);
	} catch {
		throw new ApiError(503, 'The job board backend is unreachable right now.');
	}
	if (!response.ok) {
		let detail = `Request failed (${response.status})`;
		try {
			const body = await response.json();
			if (body?.detail) detail = typeof body.detail === 'string' ? body.detail : detail;
		} catch {
			/* keep default detail */
		}
		throw new ApiError(response.status, detail);
	}
	return response.json() as Promise<T>;
}

export function getJobs(query: Record<string, string>): Promise<Paginated<Job>> {
	return api<Paginated<Job>>(`/api/jobs?${new URLSearchParams(query).toString()}`);
}

export function getJob(id: number): Promise<Job> {
	return api<Job>(`/api/jobs/${id}`);
}

export function getCompanies(
	query: Record<string, string> = {}
): Promise<Paginated<CompanyRecord>> {
	return api<Paginated<CompanyRecord>>(
		`/api/companies?${new URLSearchParams(query).toString()}`
	);
}

export function getCategories(): Promise<{ categories: CategoryInfo[] }> {
	return api<{ categories: CategoryInfo[] }>(`/api/categories`);
}

export function getCountries(): Promise<CountriesResponse> {
	return api<CountriesResponse>(`/api/countries`);
}

export const SITE_URL = env.SITE_URL ?? 'http://localhost:5173';
