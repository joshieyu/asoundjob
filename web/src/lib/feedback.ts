import { PUBLIC_API_URL, clientApi } from './client';

export type JobFeedbackKind = 'wrong_category' | 'not_audio' | 'broken_description' | 'broken_link';
export type SiteFeedbackKind = 'company_suggestion' | 'general';

export interface FeedbackKindOption<T extends string = string> {
	value: T;
	label: string;
}

export const JOB_FEEDBACK_KINDS: FeedbackKindOption<JobFeedbackKind>[] = [
	{ value: 'wrong_category', label: 'Wrong category' },
	{ value: 'not_audio', label: 'Not an audio job' },
	{ value: 'broken_description', label: 'Description looks broken' },
	{ value: 'broken_link', label: 'Application link is broken' }
];

export const SITE_FEEDBACK_KINDS: FeedbackKindOption<SiteFeedbackKind>[] = [
	{ value: 'company_suggestion', label: 'Suggest a company' },
	{ value: 'general', label: 'General feedback' }
];

export interface JobFeedbackRequest {
	kind: JobFeedbackKind;
	suggested_categories?: string[] | null;
	comment?: string | null;
	submitter_email?: string | null;
}

export interface SiteFeedbackRequest {
	kind: SiteFeedbackKind;
	company_name?: string | null;
	company_url?: string | null;
	comment?: string | null;
	submitter_email?: string | null;
	page_path?: string | null;
}

interface FeedbackResponse {
	id: number;
	status: string;
	message: string;
}

export type FeedbackState =
	| { kind: 'idle' }
	| { kind: 'submitting' }
	| { kind: 'success'; message: string }
	| { kind: 'error'; message: string };

export async function submitJobFeedback(
	jobId: number,
	body: JobFeedbackRequest
): Promise<FeedbackState> {
	try {
		const result = await clientApi<FeedbackResponse>(`/api/jobs/${jobId}/feedback`, {
			method: 'POST',
			body
		});
		return { kind: 'success', message: result.message };
	} catch (err) {
		if (err instanceof Error) return { kind: 'error', message: err.message };
		return { kind: 'error', message: `Could not reach the API at ${PUBLIC_API_URL}` };
	}
}

export async function submitSiteFeedback(body: SiteFeedbackRequest): Promise<FeedbackState> {
	try {
		const result = await clientApi<FeedbackResponse>('/api/feedback', {
			method: 'POST',
			body
		});
		return { kind: 'success', message: result.message };
	} catch (err) {
		if (err instanceof Error) return { kind: 'error', message: err.message };
		return { kind: 'error', message: `Could not reach the API at ${PUBLIC_API_URL}` };
	}
}
