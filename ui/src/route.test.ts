import { test } from 'node:test'
import assert from 'node:assert/strict'
import { buildHash, parseHash } from './route.ts'

test('parseHash reads a deal route with the exact folder', () => {
  const r = parseHash('#/deals/' + encodeURIComponent('Bayou Bistro & Grill'))
  assert.deepEqual(r, { view: 'deal', folder: 'Bayou Bistro & Grill' })
})

test('buildHash and parseHash round-trip folders with an apostrophe, an ampersand and spaces', () => {
  for (const folder of ["Mama Rosa's Kitchen", 'Bayou Bistro & Grill', 'A/B 100% #1?x=y']) {
    const h = buildHash({ view: 'deal', folder })
    assert.ok(h.startsWith('#/deals/'), h)
    assert.ok(!h.slice(8).includes('&'), 'ampersand must be encoded in the hash')
    assert.deepEqual(parseHash(h), { view: 'deal', folder })
  }
})

test('buildHash of the pipeline route', () => {
  assert.equal(buildHash({ view: 'pipeline' }), '#/pipeline')
})

test('empty, pipeline, unknown and malformed hashes give the pipeline route without throwing', () => {
  assert.deepEqual(parseHash(''), { view: 'pipeline' })
  assert.deepEqual(parseHash('#'), { view: 'pipeline' })
  assert.deepEqual(parseHash('#/pipeline'), { view: 'pipeline' })
  assert.deepEqual(parseHash('#/nowhere'), { view: 'pipeline' })
  assert.deepEqual(parseHash('#/deals/%E0%A4%A'), { view: 'pipeline' })
  assert.deepEqual(parseHash('#/deals/'), { view: 'pipeline' })
  assert.deepEqual(parseHash('#/deals'), { view: 'pipeline' })
})
