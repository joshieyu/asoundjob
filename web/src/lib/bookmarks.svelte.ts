import { getBookmarks, toggleBookmark } from '$lib/client';

const ids = $state(new Set<number>());
let hydrated = $state(false);

export function hydrateBookmarks() {
	if (hydrated) return;
	for (const id of getBookmarks()) ids.add(id);
	hydrated = true;
}

export const bookmarks = {
	get hydrated() {
		return hydrated;
	},
	get ids() {
		return ids;
	},
	has(id: number) {
		return ids.has(id);
	},
	toggle(id: number) {
		const on = toggleBookmark(id);
		if (on) ids.add(id);
		else ids.delete(id);
		return on;
	}
};
