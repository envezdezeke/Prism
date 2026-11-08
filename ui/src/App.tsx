import { useEffect } from 'react'
import { Board } from '@/components/app/Board'
import { Button } from '@/components/ui/button'
import { fmtSimTime } from './lib/format.ts'
import { useClockStore } from './state/clockStore.ts'

export default function App() {
  const { status, now, error, load } = useClockStore()

  // The only call site of the clock endpoint outside the smoke script (D-21).
  useEffect(() => {
    void load()
  }, [load])

  return (
    <main className="mx-auto flex max-w-[1280px] flex-col gap-4 p-6">
      <header className="flex flex-col gap-1">
        <h1 className="font-display text-title font-normal">Pipeline</h1>
        {status === 'ready' && (
          <p className="text-sm text-ink-2">
            Sim time (CT) <span className="font-semibold text-ink">{fmtSimTime(now)}</span>
          </p>
        )}
      </header>
      {(status === 'idle' || status === 'loading') && <p className="text-sm text-ink-2">Loading clock.</p>}
      {status === 'error' && (
        <div role="alert" className="flex flex-col items-start gap-2 rounded-md border border-line bg-surface p-4">
          <p className="text-base font-semibold">Could not load the clock.</p>
          <p className="text-sm">{error}</p>
          <Button variant="outline" size="sm" onClick={() => void load()}>
            Retry
          </Button>
        </div>
      )}
      {status === 'ready' && <Board />}
    </main>
  )
}
