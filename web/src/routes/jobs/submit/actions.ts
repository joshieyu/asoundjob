import { PUBLIC_API_URL, clientApi } from '$lib/client';
import type { JobSubmissionRequest } from './types';

export type SubmitState =
	| { kind: 'idle' }
	| { kind: 'submitting' }
	| { kind: 'success'; message: string }
	| { kind: 'error'; message: string };

export async function submitJob(form: JobSubmissionRequest): Promise<SubmitState> {
	try {
		const result = await clientApi<{ id: number; status: string; message: string }>(
			'/api/jobs/submit',
			{ method: 'POST', body: form }
		);
		return { kind: 'success', message: result.message };
	} catch (err) {
		if (err instanceof Error) return { kind: 'error', message: err.message };
		return { kind: 'error', message: `Could not reach the API at ${PUBLIC_API_URL}` };
	}
}
