const ALLOWED_TAGS = new Set([
	'p',
	'br',
	'ul',
	'ol',
	'li',
	'strong',
	'em',
	'b',
	'i',
	'h2',
	'h3',
	'h4',
	'blockquote'
]);

const ENTITIES: Record<string, string> = {
	'&lt;': '<',
	'&gt;': '>',
	'&quot;': '"',
	'&#39;': "'",
	'&apos;': "'",
	'&nbsp;': ' ',
	'&amp;': '&'
};

export function decodeEntities(text: string): string {
	let previous = '';
	let current = text;
	while (current !== previous) {
		previous = current;
		for (const [entity, char] of Object.entries(ENTITIES)) {
			current = current.split(entity).join(char);
		}
	}
	return current;
}

function looksLikeHtml(text: string): boolean {
	return /<(p|div|br|ul|ol|li|h[1-6]|span|strong|em|b|i|a)\b/i.test(text);
}

export function renderDescription(
	raw: string | null | undefined
): { html: string | null; plain: string } {
	if (!raw) return { html: null, plain: '' };
	const html = looksLikeHtml(decodeEntities(raw)) ? sanitizeJobHtml(raw) : null;
	return { html, plain: stripHtml(raw) };
}

export function sanitizeJobHtml(html: string): string {
	let cleaned = decodeEntities(html)
		.replace(/<!--[\s\S]*?-->/g, '')
		.replace(/<(script|style|iframe|object|embed|svg|math)[\s\S]*?<\/\1>/gi, '')
		.replace(/<\/?(script|style|iframe|object|embed|svg|math)[^>]*>/gi, '');

	cleaned = cleaned.replace(/<\/?([a-zA-Z0-9-]+)(\s[^>]*)?>/g, (match, tag: string) => {
		if (!ALLOWED_TAGS.has(tag.toLowerCase())) return '';
		return match.replace(/\s[^>]*/g, '');
	});

	return cleaned.trim();
}

export function stripHtml(html: string | null | undefined): string {
	if (!html) return '';
	return decodeEntities(html)
		.replace(/<[^>]*>/g, ' ')
		.replace(/\s+/g, ' ')
		.trim();
}
