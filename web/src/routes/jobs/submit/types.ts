export interface JobSubmissionRequest {
	title: string;
	company_name: string;
	url: string;
	description: string;
	location?: string;
	remote: boolean;
	job_type?: string;
	salary_range?: string;
	experience_level?: string;
	audio_domain?: string;
	submitter_name?: string;
	submitter_email?: string;
	duration_days?: number;
}
