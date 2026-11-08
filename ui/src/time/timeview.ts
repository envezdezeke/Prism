// Pure sim-time view functions. No Date local-time use: every sim time is a
// fixed -06:00 wall-clock string, so UTC arithmetic gives exact results.
export interface StageLogEntry {
  stage: string
  entered_at: string
  exited_at?: string | null
  decision?: string | null
  why: string
}

export interface FraudBlock {
  flagged: boolean
  held: boolean
  flagged_at?: string | null
}

export interface DealLike {
  folder: string
  needed_by?: string | null
  stage: string
  stage_entered_at: string
  sla_hours: number
  sla_pct: number
  held: boolean
  watch: boolean
}

export interface DetailLike extends DealLike {
  stage_log: StageLogEntry[]
  fraud: FraudBlock
}

export interface InboxLike {
  id: string
  deal: string
  type: string
  to: string
  at: string
  options: string[]
  status: 'pending' | 'answered'
  answer?: string | null
  answered_at?: string | null
}

export interface AlertLike {
  id: string
  deal: string
  at: string
  level: 'alert' | 'escalation'
  message: string
}

// The contract's parse_sim_time accepts seconds and a fraction, so the UI does too (WR-07).
const SIM_RE = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2})(\.\d+)?)?-06:00$/
const HOUR_MS = 3600_000

export function simToMs(s: string): number {
  const m = SIM_RE.exec(s)
  if (!m) throw new Error(`not a -06:00 sim time: ${s}`)
  // -06:00 means UTC = wall clock + 6h
  const ms = m[7] === undefined ? 0 : Math.round(+`0${m[7]}` * 1000)
  return Date.UTC(+m[1], +m[2] - 1, +m[3], +m[4], +m[5], m[6] === undefined ? 0 : +m[6], ms) + 6 * HOUR_MS
}

// Inverse of simToMs: the YYYY-MM-DDTHH:mm-06:00 shape the contract's parse_sim_time accepts.
export function msToSim(ms: number): string {
  const d = new Date(ms - 6 * HOUR_MS)
  return `${d.getUTCFullYear()}-${pad2(d.getUTCMonth() + 1)}-${pad2(d.getUTCDate())}T${pad2(d.getUTCHours())}:${pad2(d.getUTCMinutes())}-06:00`
}

export function clampMs(x: number, lo: number, hi: number): number {
  return x < lo ? lo : x > hi ? hi : x
}

const DOW = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

// "Tue 11/03 3:05 PM CT" (house style, docs/MESSAGE_TEMPLATES.md)
export function fmtSimTime(s: string): string {
  const m = SIM_RE.exec(s)
  if (!m) throw new Error(`not a -06:00 sim time: ${s}`)
  const y = +m[1], mo = +m[2], d = +m[3], h = +m[4], mi = +m[5]
  const dow = DOW[new Date(Date.UTC(y, mo - 1, d)).getUTCDay()]
  const h12 = ((h + 11) % 12) + 1
  const ampm = h < 12 ? 'AM' : 'PM'
  return `${dow} ${pad2(mo)}/${pad2(d)} ${h12}:${pad2(mi)} ${ampm} CT`
}

// "26h 10m"
export function fmtDuration(ms: number): string {
  const mins = Math.max(0, Math.round(ms / 60_000))
  return `${Math.floor(mins / 60)}h ${pad2(mins % 60)}m`
}

function pad2(n: number): string {
  return n < 10 ? `0${n}` : `${n}`
}

// Stage entry in force at time t. null = the deal has not arrived yet.
export function stageAt(log: StageLogEntry[], t: number): StageLogEntry | null {
  let cur: StageLogEntry | null = null
  for (const e of log) {
    if (simToMs(e.entered_at) <= t) cur = e
    else break
  }
  return cur
}

// Time spent in the stage entry that began at `enteredAt`, as of t. Held deals freeze at flagged_at
// (contract: sla_pct freezes while held). The end of the deal's final stage entry also ends the clock
// (held, declined or closed deals stop accruing). A duration needs no limit, so it is always known.
export function dwellMsAt(deal: DetailLike, enteredAt: string, t: number): number {
  const f = deal.fraud
  const frozen = f.held && f.flagged_at != null && simToMs(f.flagged_at) <= t
  let end = frozen ? simToMs(f.flagged_at as string) : t
  const last = deal.stage_log[deal.stage_log.length - 1]
  if (last && last.entered_at === enteredAt && last.exited_at != null) {
    const exit = simToMs(last.exited_at)
    if (exit <= t && exit < end) end = exit
  }
  return end - simToMs(enteredAt)
}

// Fraction of a stage limit used. `limitHours` defaults to the deal's own sla_hours, which is the limit of
// its FINAL stage only; pass the entry's own stage limit for any earlier stage (CR-01).
export function slaPctAt(deal: DetailLike, enteredAt: string, t: number, limitHours: number = deal.sla_hours): number {
  return dwellMsAt(deal, enteredAt, t) / HOUR_MS / limitHours
}

// The contract carries one sla_hours per deal: the limit of that deal's final stage. A stage's limit is
// therefore known from the deals that end in it, and only when they all agree (a delegated committee limit
// can differ per deal). Stages with no such deal, or a disagreement, are left out: the limit is unknown.
export function stageLimitsFrom(deals: { stage: string; sla_hours: number }[]): Record<string, number> {
  const seen = new Map<string, number | null>()
  for (const d of deals) {
    const prev = seen.get(d.stage)
    if (prev === undefined) seen.set(d.stage, d.sla_hours)
    else if (prev !== d.sla_hours) seen.set(d.stage, null)
  }
  const out: Record<string, number> = {}
  for (const [stage, hours] of seen) if (hours !== null) out[stage] = hours
  return out
}

// Display rounding: round half up to 2 decimals, matches fixture values.
export function roundPct(x: number): number {
  return Math.round(x * 100) / 100
}

export function heldAt(deal: DetailLike, t: number): boolean {
  return deal.fraud.held && deal.fraud.flagged_at != null && simToMs(deal.fraud.flagged_at) <= t
}

// An answer given in this browser session (D-21): the mock API does not persist replies, so the client
// holds them in memory. `answered_at` is the UI clock time of the reply, a -06:00 sim time.
export interface SessionAnswer {
  answer: string
  answered_at: string
  note?: string
}
export type SessionAnswers = Readonly<Record<string, SessionAnswer>>

// `serverAnswered` is the raw fixture/server status. It stays true when the clock is before the answer
// time and `status` reads pending, so a screen never offers buttons the server will refuse with a 409.
export type InboxView<T extends InboxLike = InboxLike> = T & { answeredInSession: boolean; serverAnswered: boolean }

function sessionAnswerFor(answers: SessionAnswers, id: string): SessionAnswer | undefined {
  return Object.hasOwn(answers, id) ? answers[id] : undefined
}

// Requests sent by t, with the session overlay applied BEFORE the status check. A fixture answer that has
// been reached wins. Otherwise a session answer whose time is reached makes the item answered, and one
// that is still in the future leaves it pending. `answeredInSession` is true whenever an entry exists, so
// the screen can explain a pending item that was answered later in the session.
export function inboxAt<T extends InboxLike>(items: T[], t: number, answers: SessionAnswers = {}): InboxView<T>[] {
  return items
    .filter((i) => simToMs(i.at) <= t)
    .map((i) => {
      const mine = sessionAnswerFor(answers, i.id)
      const answeredInSession = mine !== undefined
      const serverAnswered = i.status === 'answered'
      if (serverAnswered && i.answered_at != null && simToMs(i.answered_at) <= t) {
        return { ...i, answeredInSession, serverAnswered }
      }
      if (mine !== undefined && simToMs(mine.answered_at) <= t) {
        return { ...i, status: 'answered' as const, answer: mine.answer, answered_at: mine.answered_at, answeredInSession, serverAnswered }
      }
      return { ...i, status: 'pending' as const, answer: null, answered_at: null, answeredInSession, serverAnswered }
    })
}

// Pending requests that still need an answer: an item answered in this session does not count, even when
// the clock has been scrubbed back before the answer (it then shows pending but is not answerable again).
export function pendingCount(view: InboxView[]): number {
  return view.filter((i) => i.status === 'pending' && !i.answeredInSession).length
}

// Human requests of one deal with the session answer applied, joined to the inbox item by deal, type and
// sent time. Run requestsAt on the result so the answer still waits for its time. A fixture answer is kept.
export function requestsWithOverlay<T extends { type: string; at: string; answer?: string | null; answered_at?: string | null }>(
  deal: string,
  requests: T[],
  inboxItems: InboxLike[],
  answers: SessionAnswers,
): T[] {
  return requests.map((r) => {
    if (r.answer != null) return r
    const item = inboxItems.find((i) => i.deal === deal && i.type === r.type && i.at === r.at)
    const mine = item === undefined ? undefined : sessionAnswerFor(answers, item.id)
    return mine === undefined ? r : { ...r, answer: mine.answer, answered_at: mine.answered_at }
  })
}

// Alerts visible at t. Needs only an `at` field, so the detail's alerts (no id or deal) work too.
// Newest first for the feed; pass 'oldest' for the detail list.
export function alertsAt<T extends { at: string }>(items: T[], t: number, order: 'newest' | 'oldest' = 'newest'): T[] {
  const sign = order === 'newest' ? -1 : 1
  return items.filter((a) => simToMs(a.at) <= t).sort((a, b) => sign * (simToMs(a.at) - simToMs(b.at)))
}

// Stage log entries that have started by t. An entry whose exit is after t (or never) is open: its exit
// time and decision are hidden until t reaches them, so a screen can never show the future (D-18).
// An entry that will exit later also hides its `why`, which explains that exit; an entry that never
// exits keeps it, since it then describes where the deal stands.
export function stageLogAt<T extends StageLogEntry>(log: T[], t: number): (T & { open: boolean })[] {
  const out: (T & { open: boolean })[] = []
  for (const e of log) {
    if (simToMs(e.entered_at) > t) continue
    const open = e.exited_at == null || simToMs(e.exited_at) > t
    if (!open) out.push({ ...e, open })
    else out.push({ ...e, exited_at: null, decision: null, why: e.exited_at == null ? e.why : '', open })
  }
  return out
}

// Requests sent by t. The answer and answered_at are shown only once answered_at has been reached.
export function requestsAt<T extends { at: string; answer?: string | null; answered_at?: string | null }>(
  requests: T[],
  t: number,
): T[] {
  return requests
    .filter((r) => simToMs(r.at) <= t)
    .map((r) => {
      const answered = r.answer != null && r.answered_at != null && simToMs(r.answered_at) <= t
      return answered ? { ...r } : { ...r, answer: null, answered_at: null }
    })
}

export interface BoardRow<T extends DetailLike = DetailLike> {
  deal: T
  stage: string
  enteredAt: string
  // Time in the shown stage entry, as of t. Always known.
  dwellMs: number
  // The shown stage's own limit in hours, or null when the contract gives no way to know it (CR-01).
  limitHours: number | null
  // Raw, unrounded SLA fraction (1 = 100%) of THAT limit, or null when the limit is unknown.
  // Round only at display time.
  slaFraction: number | null
  held: boolean
}

// One row per deal that has arrived by time t; deals not yet arrived are omitted.
// `limits` is the per-stage limit map (stageLimitsFrom over every deal); it defaults to the given details.
// The deal's own final stage always uses its own sla_hours.
export function boardAt<T extends DetailLike>(
  details: T[],
  t: number,
  limits: Record<string, number> = stageLimitsFrom(details),
): BoardRow<T>[] {
  const rows: BoardRow<T>[] = []
  for (const deal of details) {
    const cur = stageAt(deal.stage_log, t)
    if (cur === null) continue
    const limitHours = cur.stage === deal.stage ? deal.sla_hours : Object.hasOwn(limits, cur.stage) ? limits[cur.stage] : null
    rows.push({
      deal,
      stage: cur.stage,
      enteredAt: cur.entered_at,
      dwellMs: dwellMsAt(deal, cur.entered_at, t),
      limitHours,
      slaFraction: limitHours === null ? null : slaPctAt(deal, cur.entered_at, t, limitHours),
      held: heldAt(deal, t),
    })
  }
  return rows
}

// Smallest sim time strictly after t across every timestamp a screen can change on, or null.
// `extra` carries timestamps the caller holds outside the fetched data (for example in-session answers).
// Strings that are not -06:00 sim times are skipped, never thrown on.
export interface EventSource {
  stage_log: { entered_at: string; exited_at?: string | null }[]
  fraud: { flagged_at?: string | null }
  human_requests?: { at: string; answered_at?: string | null }[]
  alerts?: { at: string }[]
}

export function nextEventAfter(details: EventSource[], t: number, extra: string[] = []): string | null {
  let best: number | null = null
  const consider = (s: string | null | undefined): void => {
    if (s == null || !SIM_RE.test(s)) return
    const ms = simToMs(s)
    if (ms > t && (best === null || ms < best)) best = ms
  }
  for (const d of details) {
    for (const e of d.stage_log) {
      consider(e.entered_at)
      consider(e.exited_at)
    }
    consider(d.fraud.flagged_at)
    for (const h of d.human_requests ?? []) {
      consider(h.at)
      consider(h.answered_at)
    }
    for (const a of d.alerts ?? []) consider(a.at)
  }
  for (const s of extra) consider(s)
  // Round a time with seconds up to the next whole minute, so Next event always moves the clock forward.
  return best === null ? null : msToSim(Math.ceil(best / 60_000) * 60_000)
}

// Held first, then soonest needed-by (none last), then longest in stage, then folder name.
export function sortBoardRows<T extends DetailLike>(rows: BoardRow<T>[]): BoardRow<T>[] {
  const nb = (r: BoardRow<T>): number => {
    const s = r.deal.needed_by
    return s != null && SIM_RE.test(s) ? simToMs(s) : Number.POSITIVE_INFINITY
  }
  return [...rows].sort((a, b) => {
    if (a.held !== b.held) return a.held ? -1 : 1
    const na = nb(a), nbb = nb(b)
    if (na !== nbb) return na < nbb ? -1 : 1
    const ea = simToMs(a.enteredAt), eb = simToMs(b.enteredAt)
    if (ea !== eb) return ea - eb
    return a.deal.folder < b.deal.folder ? -1 : a.deal.folder > b.deal.folder ? 1 : 0
  })
}
