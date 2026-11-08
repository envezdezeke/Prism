import { useEffect } from 'react'
import { Board } from '@/components/app/Board'
import { Button } from '@/components/ui/button'
import { useClockStore } from './state/clockStore.ts'

export default function App() {
  const { status, error, load } = useClockStore()

  // The only call site of the clock endpoint outside the smoke script (D-21).
  useEffect(() => {
    void load()
  }, [load])

  return (
    <main className="mx-auto flex max-w-[1280px] flex-col gap-4 p-6">
      {(status === 'idle' || status === 'loading') && <p role="status" className="text-sm text-ink-2">Loading clock.</p>}
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
