import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import {
  simToMs, fmtSimTime, fmtDuration, stageAt, slaPctAt, roundPct, heldAt, inboxAt, alertsAt, boardAt,
  msToSim, clampMs, nextEventAfter, sortBoardRows, stageLogAt, requestsAt, pendingCount, requestsWithOverlay,
  stageLimitsFrom,
} from './timeview.ts'

// Repo-relative fixtures folder (ui/src/time/ -> repo root), so the test also runs on Windows.
const FX = new URL('../../../fixtures/', import.meta.url)
const load = (f: string): any => JSON.parse(readFileSync(new URL(f, FX), 'utf8'))
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

test('boardAt at the snapshot: Intake 3, Credit 1, Committee 1, Bayou held', () => {
  const rows = boardAt(Object.values(detail), SNAP)
  const counts: Record<string, number> = {}
  for (const r of rows) counts[r.stage] = (counts[r.stage] ?? 0) + 1
  assert.deepEqual(counts, { Intake: 3, Credit: 1, Committee: 1 })
  const held = rows.filter((r) => r.held).map((r) => r.deal.folder).sort()
  assert.ok(held.includes('Bayou Bistro & Grill'))
  for (const r of rows) {
    const s = deals.find((d) => d.folder === r.deal.folder)
    assert.equal(roundPct(r.slaFraction!), s.sla_pct, r.deal.folder)
    assert.equal(r.held, s.held, r.deal.folder)
  }
})

test('boardAt at the clock start returns no rows', () => {
  assert.deepEqual(boardAt(Object.values(detail), START), [])
})

test('msToSim round-trips and rolls over midnight in the fixed -06:00 offset', () => {
  assert.equal(msToSim(simToMs('2026-11-03T15:05-06:00')), '2026-11-03T15:05-06:00')
  assert.equal(msToSim(simToMs('2026-11-02T23:30-06:00') + 3600_000), '2026-11-03T00:30-06:00')
})

test('clampMs returns lo below the range, hi above it, and x inside', () => {
  assert.equal(clampMs(1, 5, 10), 5)
  assert.equal(clampMs(11, 5, 10), 10)
  assert.equal(clampMs(7, 5, 10), 7)
})

test('nextEventAfter: first event from the start is 08:30 on 11/02, then strictly increasing and terminating', () => {
  const all = Object.values(detail)
  let t = START
  const seen: string[] = []
  for (let i = 0; i < 200; i++) {
    const nxt = nextEventAfter(all, t)
    if (nxt === null) break
    assert.ok(simToMs(nxt) > t, 'strictly after')
    seen.push(nxt)
    t = simToMs(nxt)
  }
  assert.equal(seen[0], '2026-11-02T08:30-06:00')
  assert.ok(seen.length > 5 && seen.length < 200, 'terminates')
  assert.equal(nextEventAfter(all, simToMs('2026-11-06T18:00-06:00')), null)
})

test('nextEventAfter reads request, answer, alert and extra timestamps and ignores bad strings', () => {
  const d: any = {
    stage_log: [{ entered_at: '2026-11-02T08:00-06:00' }],
    fraud: {},
    human_requests: [{ at: '2026-11-02T09:00-06:00', answered_at: '2026-11-02T10:00-06:00' }, { at: 'garbage' }],
    alerts: [{ at: '2026-11-02T09:30-06:00' }],
  }
  const at = (s: string) => simToMs(s)
  assert.equal(nextEventAfter([d], at('2026-11-02T08:00-06:00')), '2026-11-02T09:00-06:00')
  assert.equal(nextEventAfter([d], at('2026-11-02T09:00-06:00')), '2026-11-02T09:30-06:00')
  assert.equal(nextEventAfter([d], at('2026-11-02T09:30-06:00')), '2026-11-02T10:00-06:00')
  assert.equal(nextEventAfter([d], at('2026-11-02T10:00-06:00')), null)
  assert.equal(nextEventAfter([d], at('2026-11-02T10:00-06:00'), ['2026-11-02T11:00-06:00']), '2026-11-02T11:00-06:00')
})

test('sortBoardRows: held first, then soonest needed-by (none last), then longest in stage, then folder', () => {
  const mk = (folder: string, held: boolean, needed_by: string | null, enteredAt: string): any => ({
    deal: { folder, needed_by },
    stage: 'Intake',
    enteredAt,
    dwellMs: 0,
    limitHours: 8,
    slaFraction: 0,
    held,
  })
  const rows = [
    mk('E', false, null, '2026-11-03T08:00-06:00'),
    mk('D', false, '2026-11-06T15:00-06:00', '2026-11-03T08:00-06:00'),
    mk('C', false, '2026-11-05T15:00-06:00', '2026-11-04T08:00-06:00'),
    mk('B', true, null, '2026-11-04T08:00-06:00'),
    mk('A', false, null, '2026-11-03T08:00-06:00'),
    mk('F', false, null, '2026-11-02T08:00-06:00'),
  ]
  const sorted = sortBoardRows(rows).map((r) => r.deal.folder)
  assert.deepEqual(sorted, ['B', 'C', 'D', 'F', 'A', 'E'])
  // input untouched
  assert.equal(rows[0].deal.folder, 'E')
})

test('slaPctAt stops accruing at the end of the final stage entry (declined deal stays flat)', () => {
  const d: any = {
    sla_hours: 8,
    fraud: { held: false, flagged_at: null },
    stage_log: [{ stage: 'Intake', entered_at: '2026-11-02T08:00-06:00', exited_at: '2026-11-02T12:00-06:00' }],
  }
  const atExit = slaPctAt(d, d.stage_log[0].entered_at, simToMs('2026-11-02T12:00-06:00'))
  const later = slaPctAt(d, d.stage_log[0].entered_at, simToMs('2026-11-05T12:00-06:00'))
  assert.equal(atExit, 0.5)
  assert.equal(later, 0.5)
  // before the exit it still accrues
  assert.equal(slaPctAt(d, d.stage_log[0].entered_at, simToMs('2026-11-02T10:00-06:00')), 0.25)
  // an open entry keeps accruing
  const open: any = { ...d, stage_log: [{ stage: 'Intake', entered_at: '2026-11-02T08:00-06:00', exited_at: null }] }
  assert.equal(slaPctAt(open, open.stage_log[0].entered_at, simToMs('2026-11-02T16:00-06:00')), 1)
})

// ---- detail-page views (plan 03)

test('alertsAt accepts items with only an at field (the detail alerts have no id or deal), newest first by default', () => {
  const items = detail["Mama Rosa's Kitchen"].alerts
  const t = simToMs('2026-11-04T18:00-06:00')
  const out = alertsAt(items, t)
  assert.equal(out.length, 2)
  assert.equal(out[0].level, 'escalation')
  assert.equal(out[1].level, 'alert')
  // before the first alert nothing is visible; at its time only the first
  assert.equal(alertsAt(items, simToMs('2026-11-04T11:59-06:00')).length, 0)
  assert.equal(alertsAt(items, simToMs('2026-11-04T12:00-06:00')).length, 1)
  assert.deepEqual(alertsAt(items, t, 'oldest').map((a: any) => a.level), ['alert', 'escalation'])
})

test('stageLogAt: Mama Rosas Intake exited, Credit still open at 10:30 and 11:00, exit and decision hidden until reached', () => {
  const log = detail["Mama Rosa's Kitchen"].stage_log
  const at1030 = stageLogAt(log, simToMs('2026-11-02T10:30-06:00'))
  assert.deepEqual(at1030.map((e) => e.stage), ['Intake', 'Credit'])
  assert.equal(at1030[0].open, false)
  assert.equal(at1030[0].decision, 'advanced')
  assert.equal(at1030[0].exited_at, '2026-11-02T10:00-06:00')
  assert.equal(at1030[1].open, true)
  assert.equal(at1030[1].exited_at, null)
  assert.equal(at1030[1].decision, null)
  // the why explains the exit at 12:00, so it stays hidden while the entry is open and the exit is in the future
  assert.equal(at1030[1].why, '')
  assert.ok(at1030[0].why.length > 0)
  // an entry that never exits keeps its why (it describes where the deal stands)
  const committee = stageLogAt(log, simToMs('2026-11-04T18:00-06:00'))[2]
  assert.equal(committee.open, true)
  assert.ok(committee.why.length > 0)
  const at1100 = stageLogAt(log, simToMs('2026-11-02T11:00-06:00'))
  assert.equal(at1100.length, 2)
  assert.equal(at1100[1].open, true)
  assert.equal(at1100[1].decision, null)
  const at1230 = stageLogAt(log, simToMs('2026-11-02T12:30-06:00'))
  assert.deepEqual(at1230.map((e) => [e.stage, e.open]), [['Intake', false], ['Credit', false], ['Committee', true]])
  assert.equal(at1230[1].decision, 'advanced')
  assert.equal(stageLogAt(log, simToMs('2026-11-02T08:00-06:00')).length, 0)
})

test('stageLogAt does not mutate its input', () => {
  const log = detail["Mama Rosa's Kitchen"].stage_log
  const before = JSON.stringify(log)
  stageLogAt(log, simToMs('2026-11-02T10:30-06:00'))
  assert.equal(JSON.stringify(log), before)
})

test('requestsAt: Mama Rosas credit_decision is unanswered at 11:00, answered approve once answered_at is reached', () => {
  const reqs = detail["Mama Rosa's Kitchen"].human_requests
  assert.equal(requestsAt(reqs, simToMs('2026-11-02T10:00-06:00')).length, 0)
  const at1100 = requestsAt(reqs, simToMs('2026-11-02T11:00-06:00'))
  assert.equal(at1100.length, 1)
  assert.equal(at1100[0].answer, null)
  assert.equal(at1100[0].answered_at, null)
  const at1200 = requestsAt(reqs, simToMs('2026-11-02T12:00-06:00'))
  assert.equal(at1200[0].answer, 'approve')
  assert.equal(at1200[0].answered_at, '2026-11-02T11:50-06:00')
  // the committee request appears at 12:15 and is never answered
  const later = requestsAt(reqs, simToMs('2026-11-04T18:00-06:00'))
  assert.equal(later.length, 2)
  assert.equal(later[1].answer, null)
})

test('Bayou Bistro and Grill: no hold and no fraud_hold request at 11:00, both by 11:35', () => {
  const d = detail['Bayou Bistro & Grill']
  assert.equal(heldAt(d, simToMs('2026-11-03T11:00-06:00')), false)
  assert.equal(heldAt(d, simToMs('2026-11-03T11:30-06:00')), true)
  assert.equal(requestsAt(d.human_requests, simToMs('2026-11-03T11:00-06:00')).length, 0)
  assert.equal(requestsAt(d.human_requests, simToMs('2026-11-03T11:34-06:00')).length, 0)
  assert.equal(requestsAt(d.human_requests, simToMs('2026-11-03T11:35-06:00')).length, 1)
  // the hold decision is hidden before the stage exits at 11:30
  const before = stageLogAt(d.stage_log, simToMs('2026-11-03T11:00-06:00'))
  assert.equal(before[0].open, true)
  assert.equal(before[0].decision, null)
  assert.equal(before[0].why, '')
  assert.equal(stageLogAt(d.stage_log, simToMs('2026-11-03T11:30-06:00'))[0].decision, 'held')
})

// ---- session-answer overlay (plan 04, D-21)
const ANSWER_001 = { 'inbox-001': { answer: 'approve', answered_at: '2026-11-04T18:00-06:00' } }

test('overlay: inboxAt with no third argument behaves as before, and an empty overlay changes nothing', () => {
  const plain = inboxAt(inbox, SNAP)
  const withEmpty = inboxAt(inbox, SNAP, {})
  assert.deepEqual(plain.map((i) => [i.id, i.status, i.answer]), withEmpty.map((i) => [i.id, i.status, i.answer]))
  assert.ok(plain.every((i) => i.answeredInSession === false))
})

test('overlay: inbox-001 answered approve at 18:00 shows answered from 18:00, pending (still flagged in session) at 17:00', () => {
  const at1800 = inboxAt(inbox, simToMs('2026-11-04T18:00-06:00'), ANSWER_001).find((i) => i.id === 'inbox-001')!
  assert.equal(at1800.status, 'answered')
  assert.equal(at1800.answer, 'approve')
  assert.equal(at1800.answered_at, '2026-11-04T18:00-06:00')
  assert.equal(at1800.answeredInSession, true)
  const at1700 = inboxAt(inbox, simToMs('2026-11-04T17:00-06:00'), ANSWER_001).find((i) => i.id === 'inbox-001')!
  assert.equal(at1700.status, 'pending')
  assert.equal(at1700.answer, null)
  assert.equal(at1700.answered_at, null)
  assert.equal(at1700.answeredInSession, true)
})

test('overlay: a fixture-answered item keeps its fixture answer even when the overlay has an entry for it', () => {
  const o = { 'inbox-005': { answer: 'decline', answered_at: '2026-11-04T18:00-06:00' } }
  const item = inboxAt(inbox, SNAP, o).find((i) => i.id === 'inbox-005')!
  assert.equal(item.status, 'answered')
  assert.equal(item.answer, 'approve')
  assert.equal(item.answered_at, '2026-11-02T11:50-06:00')
})

test('overlay: applied before the status filter, so a pending fixture item becomes answered once the overlay time is reached', () => {
  const view = inboxAt(inbox, SNAP, ANSWER_001)
  assert.deepEqual(view.filter((i) => i.status === 'answered').map((i) => i.id).sort(), ['inbox-001', 'inbox-005'])
  assert.deepEqual(view.filter((i) => i.status === 'pending').map((i) => i.id).sort(), ['inbox-002', 'inbox-003', 'inbox-004'])
})

test('overlay: inboxAt does not mutate its inputs and ignores inherited keys such as __proto__', () => {
  const before = JSON.stringify(inbox)
  inboxAt(inbox, SNAP, ANSWER_001)
  assert.equal(JSON.stringify(inbox), before)
  const view = inboxAt([{ ...inbox[0], id: '__proto__' }], SNAP, {})
  assert.equal(view[0].answeredInSession, false)
})

test('overlay: pendingCount is 4 at the fixture snapshot with no overlay and 3 after answering inbox-001', () => {
  assert.equal(pendingCount(inboxAt(inbox, SNAP)), 4)
  assert.equal(pendingCount(inboxAt(inbox, SNAP, ANSWER_001)), 3)
})

test('overlay: pendingCount does not count an item answered in session even when the clock is scrubbed back before the answer', () => {
  const view = inboxAt(inbox, simToMs('2026-11-04T17:00-06:00'), ANSWER_001)
  assert.equal(view.find((i) => i.id === 'inbox-001')!.status, 'pending')
  assert.equal(pendingCount(view), 3)
})

test('overlay: requestsWithOverlay joins by deal, type and at; requestsAt hides the answer until the overlay time', () => {
  const reqs = detail['Lone Star Dental'].human_requests
  const joined = requestsWithOverlay('Lone Star Dental', reqs, inbox, ANSWER_001)
  assert.equal(joined.length, 1)
  assert.equal(joined[0].answer, 'approve')
  assert.equal(joined[0].answered_at, '2026-11-04T18:00-06:00')
  assert.equal(requestsAt(joined, simToMs('2026-11-04T18:00-06:00'))[0].answer, 'approve')
  assert.equal(requestsAt(joined, simToMs('2026-11-04T17:00-06:00'))[0].answer, null)
  // the input requests are untouched
  assert.equal(reqs[0].answer, null)
})

test('overlay: requestsWithOverlay leaves other deals, other types and fixture answers alone', () => {
  const mama = detail["Mama Rosa's Kitchen"].human_requests
  const out = requestsWithOverlay("Mama Rosa's Kitchen", mama, inbox, ANSWER_001)
  assert.deepEqual(out, mama)
  const o = { 'inbox-005': { answer: 'decline', answered_at: '2026-11-04T18:00-06:00' } }
  assert.equal(requestsWithOverlay("Mama Rosa's Kitchen", mama, inbox, o)[0].answer, 'approve')
  const none = requestsWithOverlay('Lone Star Dental', detail['Lone Star Dental'].human_requests, inbox, {})
  assert.equal(none[0].answer, null)
})

// CR-01: an earlier stage is measured against THAT stage's limit, not the final stage's sla_hours.
test('CR-01 stageLimitsFrom: limit per stage from deals that end in it, only when they agree', () => {
  const limits = stageLimitsFrom(deals)
  assert.equal(limits.Intake, 8)
  assert.equal(limits.Credit, 48)
  assert.equal(limits.Committee, 48)
  assert.equal(limits.Closed, undefined)
  const split = stageLimitsFrom([
    { stage: 'Committee', sla_hours: 48 },
    { stage: 'Committee', sla_hours: 24 },
  ] as any)
  assert.equal(split.Committee, undefined)
})

test('CR-01 Lone Star Dental at Intake on Tue 11/03 12:00 shows 44% of an 8h limit, not 7% of 48h', () => {
  const t = simToMs('2026-11-03T12:00-06:00')
  const row = boardAt([detail['Lone Star Dental']], t, stageLimitsFrom(deals))[0]
  assert.equal(row.stage, 'Intake')
  assert.equal(row.limitHours, 8)
  assert.equal(row.dwellMs, 3.5 * 3600_000)
  assert.equal(roundPct(row.slaFraction!), 0.44)
})

test('CR-01 an earlier stage whose limit is unknown gives an unknown SLA, never the final stage limit', () => {
  const t = simToMs('2026-11-03T12:00-06:00')
  const row = boardAt([detail['Lone Star Dental']], t, {})[0]
  assert.equal(row.limitHours, null)
  assert.equal(row.slaFraction, null)
  assert.equal(row.dwellMs, 3.5 * 3600_000)
  // the deal's own final stage always uses its own limit
  const end = boardAt([detail['Lone Star Dental']], SNAP, {})[0]
  assert.equal(end.limitHours, 48)
  assert.notEqual(end.slaFraction, null)
})

// WR-03: an item the server already answered, viewed before its answer time, must not look answerable.
test('WR-03 inboxAt keeps serverAnswered on an item the fixture answers later in the run', () => {
  const before = inboxAt(inbox, simToMs('2026-11-02T11:00-06:00')).find((i) => i.id === 'inbox-005')!
  assert.equal(before.status, 'pending')
  assert.equal(before.serverAnswered, true)
  assert.equal(before.answer, null)
  const after = inboxAt(inbox, simToMs('2026-11-02T12:00-06:00')).find((i) => i.id === 'inbox-005')!
  assert.equal(after.status, 'answered')
  assert.equal(after.serverAnswered, true)
  // a request the server has not answered stays answerable
  const open = inboxAt(inbox, SNAP).find((i) => i.status === 'pending')!
  assert.equal(open.serverAnswered, false)
  // a session answer does not make it serverAnswered
  const o = { [open.id]: { answer: 'approve', answered_at: '2026-11-04T18:00-06:00' } }
  assert.equal(inboxAt(inbox, SNAP, o).find((i) => i.id === open.id)!.serverAnswered, false)
})
