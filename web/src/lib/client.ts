import { env } from '$env/dynamic/public';

export const PUBLIC_API_URL = env.PUBLIC_API_URL ?? 'http://127.0.0.1:8000';

const TOKEN_KEY = 'asj:admin-token';

export function getToken(): string | null {
	if (typeof window === 'undefined') return null;
	return window.sessionStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null): void {
	if (typeof window === 'undefined') return;
	if (token) window.sessionStorage.setItem(TOKEN_KEY, token);
	else window.sessionStorage.removeItem(TOKEN_KEY);
}

export class ClientApiError extends Error {
	status: number;
	constructor(status: number, message: string) {
		super(message);
		this.status = status;
	}
}

export async function clientApi<T>(
	path: string,
	options: { method?: string; body?: unknown } = {}
): Promise<T> {
	const headers: Record<string, string> = {};
	if (options.body !== undefined) headers['Content-Type'] = 'application/json';
	const token = getToken();
	if (token) headers['Authorization'] = `Bearer ${token}`;

	let response: Response;
	try {
		response = await fetch(`${PUBLIC_API_URL}${path}`, {
			method: options.method ?? 'GET',
			headers,
			body: options.body !== undefined ? JSON.stringify(options.body) : undefined
		});
	} catch {
		throw new ClientApiError(503, 'Cannot reach the API.');
	}
	if (response.status === 401) setToken(null);
	if (!response.ok) {
		let detail = `Request failed (${response.status})`;
		try {
			const body = await response.json();
			if (body?.detail) detail = typeof body.detail === 'string' ? body.detail : detail;
		} catch {
			/* keep default */
		}
		throw new ClientApiError(response.status, detail);
	}
	return response.json() as Promise<T>;
}

const FLAG_KEY = 'asj:flags';

export function getFlags(): Set<number> {
	if (typeof window === 'undefined') return new Set();
	try {
		return new Set(JSON.parse(window.localStorage.getItem(FLAG_KEY) ?? '[]') as number[]);
	} catch {
		return new Set();
	}
}

export function toggleFlag(id: number): boolean {
	const flags = getFlags();
	if (flags.has(id)) {
		flags.delete(id);
	} else {
		flags.add(id);
	}
	window.localStorage.setItem(FLAG_KEY, JSON.stringify([...flags]));
	return flags.has(id);
}
