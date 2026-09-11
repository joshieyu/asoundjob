/**
 * Serialize a JSON-LD object for injection into an inline `<script>` element.
 *
 * `JSON.stringify` leaves `<`, `>` and `&` untouched, so any string reaching it
 * — job titles and company names are scraped from third-party careers pages and
 * are never sanitized — can close the script element with `</script>` and run
 * arbitrary markup. Escaping those three characters as `\uXXXX` keeps the output
 * valid JSON (the parsed values are unchanged) while making it inert in HTML.
 */
export function serializeJsonLd(value: unknown): string {
	return JSON.stringify(value)
		.replace(/</g, '\\u003c')
		.replace(/>/g, '\\u003e')
		.replace(/&/g, '\\u0026');
}
