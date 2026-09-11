import { test } from 'node:test';
import assert from 'node:assert/strict';
import { serializeJsonLd } from './jsonld.ts';

// Scraped job titles and company names reach the JSON-LD object unsanitized.
const breakout = 'Sound Designer </script><img src=x onerror=alert(1)>';

test('a title containing </script> cannot close the script element', () => {
	const serialized = serializeJsonLd({ title: breakout });
	assert.ok(!serialized.includes('</script>'));
	assert.ok(!serialized.includes('<'));
	assert.ok(!serialized.includes('>'));
	assert.ok(serialized.includes('\\u003c/script\\u003e'));
});

test('escaping survives round-tripping — the parsed value is unchanged', () => {
	const parsed = JSON.parse(serializeJsonLd({ title: breakout }));
	assert.equal(parsed.title, breakout);
});

test('every field is escaped, not just known ones', () => {
	const serialized = serializeJsonLd({
		title: breakout,
		hiringOrganization: { name: 'Acme </script><script>alert(2)</script>' },
		description: '<p>Mix & master</p>'
	});
	assert.ok(!/[<>&]/.test(serialized));
	const parsed = JSON.parse(serialized);
	assert.equal(parsed.hiringOrganization.name, 'Acme </script><script>alert(2)</script>');
	assert.equal(parsed.description, '<p>Mix & master</p>');
});

test('ampersands are escaped so entities cannot be smuggled in', () => {
	const serialized = serializeJsonLd({ title: 'Foley & Co' });
	assert.equal(serialized, '{"title":"Foley \\u0026 Co"}');
});
