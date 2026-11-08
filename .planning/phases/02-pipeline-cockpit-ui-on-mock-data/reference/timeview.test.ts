import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { simToMs, fmtSimTime, fmtDuration, stageAt, slaPctAt, roundPct, heldAt, inboxAt, alertsAt } from './timeview.ts'

const FX = '/Users/jes/Goldman-I/fixtures/'
const load = (f: string): any => JSON.parse(readFileSync(FX + f, 'utf8'))
const deals: any[] = load('deals.json')
const detail: Record<string, any> = load('deal_detail.json')
const inbox: any[] = load('inbox.json')
const alerts: any[] = load('alerts.json')
const clock = load('clock.json')
const SNAP = simToMs(clock.now)
const START = simToMs(clock.start)

test('formatters match house style', () => {
  assert.equal(fmtSimTime('2026-11-03T15:05-06:00'), 'Tue 11/03 3:05 PM CT')
  assert.equal(fmtSimTime('2026-11-02T08:00-06:00'), 'Mon 11/02 8:00 AM CT')
  assert.equal(fmtSimTime('2026-11-02T00:30-06:00'), 'Mon 11/02 12:30 AM CT')
  assert.equal(fmtDuration(26 * 3600_000 + 10 * 60_000), '26h 10m')
  assert.equal(fmtDuration(3 * 3600_000 + 5 * 60_000), '3h 05m')
})

test('stage at snapshot equals fixture summary stage and stage_entered_at', () => {
  for (const s of deals) {
    const cur = stageAt(detail[s.folder].stage_log, SNAP)
    assert.ok(cur, `${s.folder} should have arrived`)
    assert.equal(cur.stage, s.stage, s.folder)
    assert.equal(cur.entered_at, s.stage_entered_at, s.folder)
  }
})

test('SLA recomputed at snapshot reproduces every fixture sla_pct (with hold freeze)', () => {
  for (const s of deals) {
    const d = detail[s.folder]
    const cur = stageAt(d.stage_log, SNAP)!
    const pct = roundPct(slaPctAt(d, cur.entered_at, SNAP))
    assert.equal(pct, s.sla_pct, s.folder)
  }
})

test('held state and frozen SLA: Bayou stays in Intake and freezes at 11:30', () => {
  const d = detail["Bayou Bistro & Grill"]
  assert.equal(heldAt(d, SNAP), true)
  const cur = stageAt(d.stage_log, SNAP)!
  assert.equal(cur.stage, 'Intake')
  // Same answer 3 days later: frozen, not growing
  const later = slaPctAt(d, cur.entered_at, SNAP + 48 * 3600_000)
  assert.equal(roundPct(later), 0.44)
  // Before the flag: not held yet
  const before = simToMs('2026-11-03T11:00-06:00')
  assert.equal(heldAt(d, before), false)
})

test('deals not arrived at clock start are hidden; Mama Rosa arrives 08:30 on 11/02', () => {
  const arrived = deals.filter((s) => stageAt(detail[s.folder].stage_log, START) !== null).map((s) => s.folder)
  assert.deepEqual(arrived, [])
  const at0830 = simToMs('2026-11-02T08:30-06:00')
  const arrived2 = deals.filter((s) => stageAt(detail[s.folder].stage_log, at0830) !== null).map((s) => s.folder)
  assert.deepEqual(arrived2, ["Mama Rosa's Kitchen"])
})

test('inbox at snapshot equals fixture status and answer', () => {
  const view = inboxAt(inbox, SNAP)
  assert.equal(view.length, inbox.length)
  for (const v of view) {
    const f = inbox.find((i) => i.id === v.id)
    assert.equal(v.status, f.status)
    assert.equal(v.answer, f.answer)
  }
})

test('inbox answered_at gate: inbox-005 pending before 11:50 on 11/02, answered after', () => {
  const before = simToMs('2026-11-02T11:00-06:00')
  const after = simToMs('2026-11-02T12:00-06:00')
  const b = inboxAt(inbox, before).find((i) => i.id === 'inbox-005')!
  const a = inboxAt(inbox, after).find((i) => i.id === 'inbox-005')!
  assert.equal(b.status, 'pending')
  assert.equal(a.status, 'answered')
  assert.equal(a.answer, 'approve')
})

test('alerts visible at snapshot are all three, newest first', () => {
  const view = alertsAt(alerts, SNAP)
  assert.deepEqual(view.map((a) => a.id), ['alert-003', 'alert-002', 'alert-001'])
  const early = alertsAt(alerts, simToMs('2026-11-04T13:00-06:00'))
  assert.deepEqual(early.map((a) => a.id), ['alert-001'])
})

test('board counts at snapshot match deals.json stage distribution', () => {
  const counts: Record<string, number> = {}
  for (const s of deals) {
    const cur = stageAt(detail[s.folder].stage_log, SNAP)!
    counts[cur.stage] = (counts[cur.stage] ?? 0) + 1
  }
  assert.deepEqual(counts, { Intake: 3, Credit: 1, Committee: 1 })
})
