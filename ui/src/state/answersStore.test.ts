import { test, beforeEach } from 'node:test'
import assert from 'node:assert/strict'
import { useAnswersStore } from './answersStore.ts'

beforeEach(() => useAnswersStore.setState({ answers: {} }))

test('record stores the answer and the clock time, with the trimmed note only when there is one', () => {
  useAnswersStore.getState().record('inbox-001', 'approve', '2026-11-04T18:00-06:00', '  call me ')
  useAnswersStore.getState().record('inbox-002', 'decline', '2026-11-04T18:00-06:00', '   ')
  const a = useAnswersStore.getState().answers
  assert.deepEqual(a['inbox-001'], { answer: 'approve', answered_at: '2026-11-04T18:00-06:00', note: 'call me' })
  assert.deepEqual(a['inbox-002'], { answer: 'decline', answered_at: '2026-11-04T18:00-06:00' })
})

test('a second record for the same item is ignored: at most one reply per item per session', () => {
  useAnswersStore.getState().record('inbox-001', 'approve', '2026-11-04T18:00-06:00')
  useAnswersStore.getState().record('inbox-001', 'decline', '2026-11-04T19:00-06:00')
  assert.equal(useAnswersStore.getState().answers['inbox-001'].answer, 'approve')
})
