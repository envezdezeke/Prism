import { useEffect } from 'react'
import { Board } from '@/components/app/Board'
import { ClockBar } from '@/components/app/ClockBar'
import { DealDetail } from '@/components/app/DealDetail'
import { buildHash } from './route.ts'
import type { Route } from './route.ts'
import { useClockStore } from './state/clockStore.ts'
import { useUiStore } from './state/uiStore.ts'

// The rail lists only views that exist (D-11). Plan 04 adds Inbox and Alerts when those screens are built.
const NAV_ITEMS: { id: Route['view']; label: string; route: Route }[] = [
  { id: 'pipeline', label: 'Pipeline', route: { view: 'pipeline' } },
]

// Pipeline stays the active item while one of its deals is open.
const isActive = (item: Route['view'], current: Route['view']): boolean =>
  item === current || (item === 'pipeline' && current === 'deal')

function Rail() {
  const current = useUiStore((s) => s.route.view)
  return (
    <aside aria-label="Primary" className="w-50 shrink-0 border-r border-line bg-surface">
      <p className="px-4 py-4 text-sm font-semibold text-ink">Prism</p>
      <nav aria-label="Views">
        <ul className="flex flex-col">
          {NAV_ITEMS.map((item) => {
            const active = isActive(item.id, current)
            return (
              <li key={item.id}>
                <a
                  href={buildHash(item.route)}
                  aria-current={active ? 'page' : undefined}
                  className={`flex h-9 items-center border-l-2 px-4 text-sm ${
                    active ? 'border-navy font-semibold text-navy' : 'border-transparent text-ink-2 hover:bg-subtle'
                  }`}
                >
                  {item.label}
                </a>
              </li>
            )
          })}
        </ul>
      </nav>
    </aside>
  )
}

export default function App() {
  const status = useClockStore((s) => s.status)
  const load = useClockStore((s) => s.load)
  const route = useUiStore((s) => s.route)

  // The only call site of the clock endpoint outside the smoke script (D-21).
  useEffect(() => {
    void load()
  }, [load])

  // The document title is the current page name (the deal view sets its own once the name is known).
  useEffect(() => {
    if (route.view === 'pipeline') document.title = 'Pipeline · Prism'
  }, [route])

  return (
    <>
      <ClockBar />
      <div className="flex">
        <Rail />
        <main className="flex min-w-0 flex-1 flex-col gap-4 p-6">
          {status === 'ready' && (route.view === 'deal' ? <DealDetail key={route.folder} folder={route.folder} /> : <Board />)}
        </main>
      </div>
    </>
  )
}
