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

const SIM_RE = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})-06:00$/
const HOUR_MS = 3600_000

export function simToMs(s: string): number {
  const m = SIM_RE.exec(s)
  if (!m) throw new Error(`not a -06:00 sim time: ${s}`)
  // -06:00 means UTC = wall clock + 6h
  return Date.UTC(+m[1], +m[2] - 1, +m[3], +m[4], +m[5]) + 6 * HOUR_MS
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

// Held deals freeze their SLA at flagged_at (contract: sla_pct freezes while held).
export function slaPctAt(deal: DetailLike, enteredAt: string, t: number): number {
  const f = deal.fraud
  const frozen = f.held && f.flagged_at != null && simToMs(f.flagged_at) <= t
  const end = frozen ? simToMs(f.flagged_at as string) : t
  return (end - simToMs(enteredAt)) / HOUR_MS / deal.sla_hours
}

// Display rounding: round half up to 2 decimals, matches fixture values.
export function roundPct(x: number): number {
  return Math.round(x * 100) / 100
}

export function heldAt(deal: DetailLike, t: number): boolean {
  return deal.fraud.held && deal.fraud.flagged_at != null && simToMs(deal.fraud.flagged_at) <= t
}

export function inboxAt(items: InboxLike[], t: number): InboxLike[] {
  return items
    .filter((i) => simToMs(i.at) <= t)
    .map((i) => {
      const answered = i.status === 'answered' && i.answered_at != null && simToMs(i.answered_at) <= t
      return answered
        ? { ...i }
        : { ...i, status: 'pending' as const, answer: null, answered_at: null }
    })
}

export function alertsAt(items: AlertLike[], t: number): AlertLike[] {
  return items.filter((a) => simToMs(a.at) <= t).sort((a, b) => simToMs(b.at) - simToMs(a.at))
}

export interface BoardRow<T extends DetailLike = DetailLike> {
  deal: T
  stage: string
  enteredAt: string
  // Raw, unrounded SLA fraction (1 = 100%). Round only at display time.
  slaFraction: number
  held: boolean
}

// One row per deal that has arrived by time t; deals not yet arrived are omitted.
export function boardAt<T extends DetailLike>(details: T[], t: number): BoardRow<T>[] {
  const rows: BoardRow<T>[] = []
  for (const deal of details) {
    const cur = stageAt(deal.stage_log, t)
    if (cur === null) continue
    rows.push({
      deal,
      stage: cur.stage,
      enteredAt: cur.entered_at,
      slaFraction: slaPctAt(deal, cur.entered_at, t),
      held: heldAt(deal, t),
    })
  }
  return rows
}
