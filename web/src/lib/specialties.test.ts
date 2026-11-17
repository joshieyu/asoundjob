import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { SPECIALTIES } from './specialties.ts';

const categories: { id: string }[] = JSON.parse(
	readFileSync(new URL('../../../data/audio_job_categories.json', import.meta.url), 'utf8')
).job_categories;

test('every job category has a specialty page', () => {
	const covered = new Set(SPECIALTIES.map((s) => s.id));
	for (const { id } of categories) assert.ok(covered.has(id), `no specialty page for ${id}`);
	assert.equal(SPECIALTIES.length, categories.length);
});

test('specialty slugs are unique, URL-safe and never numeric', () => {
	const slugs = SPECIALTIES.map((s) => s.slug);
	assert.equal(new Set(slugs).size, slugs.length);
	for (const slug of slugs) {
		assert.match(slug, /^[a-z0-9]+(?:-[a-z0-9]+)*$/);
		assert.doesNotMatch(slug, /^\d+$/);
		assert.notEqual(slug, 'submit');
	}
});
