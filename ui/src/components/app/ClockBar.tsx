import { useMemo, useState } from 'react'
import { ChevronsRight, Pause, Play, RotateCcw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useDealDetails, useDeals, useGraph } from '../../data/queries.ts'
import { clusterForDeal, latestHold } from '../../graph/graphview.ts'
import type { GGraph } from '../../graph/graphview.ts'
import { fmtSimTime } from '../../lib/format.ts'
import { buildHash } from '../../route.ts'
import { useClockStore } from '../../state/clockStore.ts'
import { nextEventAfter, simToMs } from '../../time/timeview.ts'
import { ErrorState, LoadingState } from './Primitives.tsx'

const HOLD_LINE_MS = 24 * 3600_000

const barClass ='flex min-h-14 flex-wrap items-center gap-x-4 gap-y-1 border-b border-line bg-surface px-6 py-2'

// Top bar: the sim clock and nothing else. Every control updates the client clock first (clamped),
// then the store confirms an absolute target to the API (D-21).
export function ClockBar() {
  const { status, now, start, end, error, playing, syncError, load, advanceHours, goTo, replay, play, pause } =
    useClockStore()
  const deals = useDeals()
  const folders = useMemo(() => (deals.data ?? []).map((d) => d.folder), [deals.data])
  const { details, isLoading } = useDealDetails(folders)
  const graph = useGraph()
  // The typed value is a draft until Go; otherwise the field follows the clock.
  const [draft, setDraft] = useState<string | null>(null)
  const [rangeMessage, setRangeMessage] = useState(false)

  if (status === 'idle' || status === 'loading') {
    return (
      <div className={barClass}>
        <LoadingState>Loading clock.</LoadingState>
      </div>
    )
  }
  if (status === 'error') {
    return (
      <div className={barClass}>
        <ErrorState heading="Could not load the clock." message={error} onRetry={() => void load()} />
      </div>
    )
  }

  const nowMs = simToMs(now)
  const atEnd = nowMs >= simToMs(end)
  // One alert line for the most recent hold in the last sim day (D-31).
  const hold = isLoading ? null : latestHold(details, nowMs)
  const freshHold = hold !== null && nowMs - hold.ms <= HOLD_LINE_MS ? hold : null
  const holdCluster =
    freshHold && graph.data ? (clusterForDeal(graph.data as GGraph, freshHold.folder)?.id ?? null) : null
  const nextEvent = isLoading ? null : nextEventAfter(details, nowMs)
  const value = draft ?? now.slice(0, 16)

  const submitGoTo = (): void => {
    const sim = `${value}-06:00`
    let ok = false
    try {
      const ms = simToMs(sim)
      ok = ms >= simToMs(start) && ms <= simToMs(end)
    } catch {
      ok = false
    }
    if (!ok) {
      setRangeMessage(true)
      return
    }
    setRangeMessage(false)
    setDraft(null)
    goTo(sim)
  }

  return (
    <div className={navyBarClass}>
      <div className="flex items-baseline gap-2">
        <span className={barLabel}>Sim time (CT)</span>
        <span className="text-base font-bold tabular-nums">{fmtSimTime(now)}</span>
      </div>
      {freshHold !== null && (
        <p key={freshHold.folder} role="status" className="order-last flex basis-full animate-fade-in flex-wrap items-baseline gap-x-2 text-sm">
          <span className="font-semibold text-hold">Held {fmtSimTime(freshHold.at)}</span>
          <span className="text-ink">
            {freshHold.name}, linked to {freshHold.linked} {freshHold.linked === 1 ? 'deal' : 'deals'}
          </span>
          {holdCluster !== null && (
            <a href={buildHash({ view: 'graph', clusterId: holdCluster })} className="font-semibold text-hold underline-offset-2 hover:underline">
              Investigate ring →
            </a>
          )}
        </p>
      )}
      <div className="ml-auto flex flex-wrap items-center gap-2">
        <Button variant="outline" disabled={atEnd} onClick={() => advanceHours(1)}>
          +1h
        </Button>
        <Button variant="outline" disabled={atEnd} onClick={() => advanceHours(6)}>
          +6h
        </Button>
        <Button variant="outline" disabled={atEnd} onClick={() => advanceHours(24)}>
          +1 day
        </Button>
        <Button
          variant="outline"
          disabled={nextEvent === null}
          title={nextEvent === null ? 'No later event' : undefined}
          onClick={() => nextEvent !== null && goTo(nextEvent)}
        >
          <ChevronsRight aria-hidden="true" />
          Next event
        </Button>
        {playing ? (
          <Button variant="outline" onClick={pause}>
            <Pause aria-hidden="true" />
            Pause
          </Button>
        ) : (
          <Button variant="outline" disabled={atEnd} onClick={play}>
            <Play aria-hidden="true" />
            Play
          </Button>
        )}
        <Button onClick={replay} className="bg-sky font-bold text-navy hover:bg-sky hover:brightness-110 focus-visible:outline-sky">
          <RotateCcw aria-hidden="true" />
          Replay from start
        </Button>
        <label className="flex items-center gap-2">
          <span className={barLabel}>Go to</span>
          <Input
            type="datetime-local"
            step={60}
            min={start.slice(0, 16)}
            max={end.slice(0, 16)}
            value={value}
            onChange={(e) => setDraft(e.target.value)}
            className="w-48"
          />
        </label>
        <Button variant="outline" onClick={submitGoTo}>
          Go
        </Button>
      </div>
      {(nextEvent === null && !isLoading) || rangeMessage || syncError !== '' ? (
        <div className="flex basis-full flex-wrap justify-end gap-x-4 text-xs text-surface/80">
          {nextEvent === null && !isLoading && <p>No later event</p>}
          {rangeMessage && (
            <p>
              Enter a time between {fmtSimTime(start)} and {fmtSimTime(end)}.
            </p>
          )}
          {syncError !== '' && (
            <p title={syncError}>The clock could not be set on the server. The screen shows {fmtSimTime(now)}.</p>
          )}
        </div>
      ) : null}
    </div>
  )
}
