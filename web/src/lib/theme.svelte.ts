export type Theme = 'light' | 'dark';

// Shared, because the header renders two toggles — one in the desktop nav, one
// in the mobile bar. Component-local state let them disagree: flipping the
// desktop control left the mobile one still claiming the old value.
let theme = $state<Theme>('light');
let started = false;

function apply(next: Theme, persist: boolean) {
	theme = next;
	document.documentElement.dataset.theme = next;
	// Read the ground back out of the cascade rather than repeating the hex here,
	// so the browser chrome can never drift from the stylesheet.
	const ground = getComputedStyle(document.documentElement)
		.getPropertyValue('--color-ground')
		.trim();
	if (ground) {
		document.querySelector('meta[name="theme-color"]')?.setAttribute('content', ground);
	}
	if (persist) {
		try {
			localStorage.setItem('asj:theme', next);
		} catch {
			// Private mode or blocked site data: the choice holds for this page
			// but will not survive a reload. Not worth surfacing.
		}
	}
}

function storedChoice(): Theme | null {
	try {
		const v = localStorage.getItem('asj:theme');
		return v === 'light' || v === 'dark' ? v : null;
	} catch {
		return null;
	}
}

export function startTheme() {
	if (started) return;
	started = true;
	// app.html's head script already resolved this before first paint; read it
	// back instead of re-deriving, so the two can't disagree.
	theme = document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light';

	// With no explicit choice on file, keep following the OS while the page is open.
	window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
		if (storedChoice()) return;
		apply(e.matches ? 'dark' : 'light', false);
	});
}

export const themeState = {
	get current() {
		return theme;
	},
	toggle() {
		apply(theme === 'dark' ? 'light' : 'dark', true);
	}
};
