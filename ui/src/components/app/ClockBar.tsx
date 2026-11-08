import { useMemo, useState } from 'react'
import { ChevronsRight, Pause, Play, RotateCcw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useDealDetails, useDeals } from '../../data/queries.ts'
import { fmtSimTime } from '../../lib/format.ts'
import { useAnswersStore } from '../../state/answersStore.ts'
import { useClockStore } from '../../state/clockStore.ts'
import { nextEventAfter, simToMs } from '../../time/timeview.ts'
import { ErrorState, LoadingState } from './Primitives.tsx'

const barClass = 'flex min-h-14 flex-wrap items-center gap-x-4 gap-y-1 border-b border-line bg-surface px-6 py-2'
// The running clock sits on a navy band with a sky rule beneath it (bolder look, D-03 amended).
// Focus rings are sky here: the global navy ring is invisible on navy (WR-06). Disabled buttons drop the
// white fill and dim, so +1h at the end of the run no longer looks clickable (IN-08).
const navyBarClass =
  'flex min-h-16 flex-wrap items-center gap-x-4 gap-y-1 border-b-4 border-sky bg-navy px-6 py-2 text-surface ' +
  '[&_button:focus-visible]:outline-sky [&_input:focus-visible]:outline-sky ' +
  '[&_button:disabled]:border-surface/30 [&_button:disabled]:bg-transparent [&_button:disabled]:text-surface/60'
const barLabel = 'text-xs font-medium uppercase tracking-wide text-surface/75'

// Top bar: the sim clock and nothing else. Every control updates the client clock first (clamped),
// then the store confirms an absolute target to the API (D-21).
export function ClockBar() {
  const { status, now, start, end, error, playing, syncError, load, advanceHours, goTo, replay, play, pause } =
    useClockStore()
  const deals = useDeals()
  const folders = useMemo(() => (deals.data ?? []).map((d) => d.folder), [deals.data])
  const { details, isLoading } = useDealDetails(folders)
  // Answers given in this session are events too: Next event stops at their time (UI-SPEC rule 11).
  const answers = useAnswersStore((s) => s.answers)
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
  const sessionTimes = Object.values(answers).map((a) => a.answered_at)
  const nextEvent = isLoading ? null : nextEventAfter(details, nowMs, sessionTimes)
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
