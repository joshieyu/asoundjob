export interface CompanyBrief {
	id: number;
	name: string;
	slug: string;
	logo_url: string | null;
}

export interface Job {
	id: number;
	title: string;
	url: string;
	location: string | null;
	country: string | null;
	country_name: string | null;
	remote: boolean;
	job_type: string | null;
	seniority: string | null;
	salary_min: number | null;
	salary_max: number | null;
	salary_currency: string | null;
	job_categories: string[];
	posted_date: string | null;
	scraped_at: string;
	expires_date: string | null;
	is_active: boolean;
	source: string;
	description?: string | null;
	company: CompanyBrief | null;
}

export interface Paginated<T> {
	items: T[];
	total: number;
	page: number;
	per_page: number;
	pages: number;
}

export interface CategoryInfo {
	id: string;
	name: string;
	description: string;
	job_count: number;
}

export interface CountryInfo {
	code: string;
	name: string;
	job_count: number;
}

export interface CountriesResponse {
	countries: CountryInfo[];
	unknown_count: number;
}

export interface CompanyRecord {
	id: number;
	name: string;
	slug: string;
	category: string;
	careers_url: string | null;
	website_url: string | null;
	logo_url: string | null;
	description: string | null;
	headquarters: string | null;
	founded: number | null;
	verified: boolean;
	source: string;
	created_at: string;
	active_jobs_count: number;
}

export type JobQuery = {
	q?: string;
	category?: string;
	seniority?: string;
	job_type?: string;
	salary_min?: number;
	salary_max?: number;
	company_id?: number;
	location?: string;
	remote?: boolean;
	include_unrelated?: boolean;
	sort?: string;
	page?: number;
	per_page?: number;
};

export function jobQueryString(query: JobQuery): string {
	const params = new URLSearchParams();
	if (query.q) params.set('q', query.q);
	if (query.category) params.set('category', query.category);
	if (query.seniority) params.set('seniority', query.seniority);
	if (query.job_type) params.set('job_type', query.job_type);
	if (query.salary_min != null) params.set('salary_min', String(query.salary_min));
	if (query.salary_max != null) params.set('salary_max', String(query.salary_max));
	if (query.company_id != null) params.set('company_id', String(query.company_id));
	if (query.location) params.set('location', query.location);
	if (query.remote) params.set('remote', 'true');
	if (query.include_unrelated) params.set('include_unrelated', 'true');
	if (query.sort) params.set('sort', query.sort);
	if (query.page && query.page > 1) params.set('page', String(query.page));
	if (query.per_page) params.set('per_page', String(query.per_page));
	return params.toString();
}
