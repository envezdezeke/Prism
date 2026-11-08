import { useEffect } from 'react'
import { Board } from '@/components/app/Board'
import { ClockBar } from '@/components/app/ClockBar'
import { useClockStore } from './state/clockStore.ts'

export default function App() {
  const status = useClockStore((s) => s.status)
  const load = useClockStore((s) => s.load)

  // The only call site of the clock endpoint outside the smoke script (D-21).
  useEffect(() => {
    void load()
  }, [load])

  return (
    <>
      <ClockBar />
      <main className="mx-auto flex max-w-[1280px] flex-col gap-4 p-6">{status === 'ready' && <Board />}</main>
    </>
  )
}
