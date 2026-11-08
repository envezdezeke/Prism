// Typed fetch wrapper. Runs under Vite and under Node (scripts/smoke.ts), so: relative imports with
// explicit .ts extensions, import type for types, and no import.meta.env.
import type { Clock, DealDetail, DealSummary } from './types.ts'

let base = ''

// Default is empty so paths stay relative and the Vite proxy handles /api. Node scripts set a host.
export function setApiBase(url: string): void {
  base = url.replace(/\/+$/, '')
}

// status 0 means the API could not be reached at all.
export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export function describeError(e: unknown): string {
  if (e instanceof ApiError) {
    if (e.status === 503) return 'The engine is not connected.'
    if (e.status === 0) return 'The API is not reachable. Start the mock server on port 8000.'
    return e.message
  }
  return 'Request failed.'
}

// Never expose a raw body or stack trace: only the API's `detail` string or a fixed message.
async function apiGet<T>(path: string): Promise<T> {
  let res: Response
  try {
    res = await fetch(base + path)
  } catch {
    throw new ApiError(0, 'network')
  }
  if (res.ok) return (await res.json()) as T

  const text = await res.text().catch(() => '')
  let detail: unknown
  try {
    detail = (JSON.parse(text) as { detail?: unknown }).detail
  } catch {
    detail = undefined
  }
  // A dev proxy with nothing behind it answers 5xx with an empty body.
  if (res.status >= 500 && text === '' && detail === undefined) throw new ApiError(0, 'network')
  throw new ApiError(
    res.status,
    typeof detail === 'string' ? detail : `Request failed (HTTP ${res.status})`,
  )
}

export function getClock(): Promise<Clock> {
  return apiGet<Clock>('/api/clock')
}

export function getDeals(): Promise<DealSummary[]> {
  return apiGet<DealSummary[]>('/api/deals')
}

export async function getDeal(folder: string): Promise<DealDetail> {
  try {
    // Folder names contain apostrophes, ampersands and spaces.
    return await apiGet<DealDetail>(`/api/deals/${encodeURIComponent(folder)}`)
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) {
      throw new ApiError(404, 'This deal is not in the run.')
    }
    throw e
  }
}
