import { getBookmarks, toggleBookmark } from '$lib/client';

// Backed by an array rather than a Set: `$state` only deep-proxies objects whose
// prototype is Object.prototype or Array.prototype, so a `Set` is handed back
// unproxied and `.add()` / `.delete()` notify nobody. An array is proxied, which
// is what makes the bookmark buttons repaint. The list is per-device and short,
// so the linear `includes` is not worth optimising away.
let ids = $state<number[]>([]);
let hydrated = $state(false);

export function hydrateBookmarks() {
	if (hydrated) return;
	hydrated = true;
	ids = [...getBookmarks()];
}

export const bookmarks = {
	get hydrated() {
		return hydrated;
	},
	get ids() {
		return ids;
	},
	has(id: number) {
		return ids.includes(id);
	},
	toggle(id: number) {
		const on = toggleBookmark(id);
		if (on) {
			if (!ids.includes(id)) ids.push(id);
		} else {
			const at = ids.indexOf(id);
			if (at !== -1) ids.splice(at, 1);
		}
		return on;
	}
};
