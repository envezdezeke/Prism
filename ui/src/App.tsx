import { useEffect } from 'react'
import { AlertsFeed } from '@/components/app/AlertsFeed'
import { Board } from '@/components/app/Board'
import { ClockBar } from '@/components/app/ClockBar'
import { AlertsFeed } from '@/components/app/AlertsFeed'
import { DealDetail } from '@/components/app/DealDetail'
import { FraudGraph } from '@/components/app/FraudGraph'
import { Inbox } from '@/components/app/Inbox'
import { usePendingCount } from './state/pendingCount.ts'
import { buildHash } from './route.ts'
import type { Route } from './route.ts'
import { useClockStore } from './state/clockStore.ts'
import { useAnswersStore } from './state/answersStore.ts'
import { useUiStore } from './state/uiStore.ts'
import { inboxAt, pendingCount, simToMs } from './time/timeview.ts'

// The rail lists only views that exist (D-11).
const NAV_ITEMS: { id: Route['view']; label: string; route: Route }[] = [
  { id: 'pipeline', label: 'Pipeline', route: { view: 'pipeline' } },
  { id: 'inbox', label: 'Inbox', route: { view: 'inbox' } },
  { id: 'alerts', label: 'Alerts', route: { view: 'alerts' } },
  { id: 'graph', label: 'Fraud graph', route: { view: 'graph', clusterId: null } },
]

const PAGE_TITLES: Partial<Record<Route['view'], string>> = {
  pipeline: 'Pipeline · Prism',
  inbox: 'Inbox · Prism',
  alerts: 'Alerts · Prism',
}

// Pipeline stays the active item while one of its deals is open.
const isActive = (item: Route['view'], current: Route['view']): boolean =>
  item === current || (item === 'pipeline' && current === 'deal')

function Rail() {
  const current = useUiStore((s) => s.route.view)
  const pending = usePendingCount()
  return (
    <aside aria-label="Primary" className="min-h-screen w-50 shrink-0 bg-navy">
      <p className="flex items-center gap-2.5 border-b border-surface/15 px-4 py-4 text-base font-bold tracking-wide text-surface">
        <img src="/prism.svg" alt="" className="size-7" />
        Prism
      </p>
      <nav aria-label="Views">
        <ul className="flex flex-col">
          {NAV_ITEMS.map((item) => {
            const active = isActive(item.id, current)
            return (
              <li key={item.id}>
                <a
                  href={buildHash(item.route)}
                  aria-current={active ? 'page' : undefined}
                  className={`flex h-9 items-center justify-between border-l-2 px-4 text-sm transition-colors duration-150 ${
                    active ? 'border-navy font-semibold text-navy' : 'border-transparent text-ink-2 hover:bg-subtle'
                  }`}
                >
                  <span>{item.label}</span>
                  {item.id === 'inbox' && pending > 0 && (
                    <span className="text-xs font-normal text-ink-2 tabular-nums" aria-label={`${pending} pending`}>
                      {pending}
                    </span>
                  )}
                </a>
              </li>
            )
          })}
        </ul>
      </nav>
    </aside>
  )
}

function Screen({ route }: { route: Route }) {
  switch (route.view) {
    case 'deal':
      return <DealDetail key={route.folder} folder={route.folder} />
    case 'inbox':
      return <Inbox />
    case 'alerts':
      return <AlertsFeed />
    case 'graph':
      return <FraudGraph clusterId={route.clusterId} />
    default:
      return <Board />
  }
}

export default function App() {
  const status = useClockStore((s) => s.status)
  const load = useClockStore((s) => s.load)
  const route = useUiStore((s) => s.route)

  // The only call site of the clock endpoint outside the smoke script (D-21).
  useEffect(() => {
    void load()
  }, [load])

  // The document title is the current page name (other views set their own).
  useEffect(() => {
    const title = PAGE_TITLES[route.view]
    if (title !== undefined) document.title = title
  }, [route])

  return (
    <>
      <ClockBar />
      <div className="flex min-h-[calc(100vh-3.5rem)]">
        <Rail />
        <main className="flex min-w-0 flex-1 flex-col gap-4 p-6">{status === 'ready' && <Screen route={route} />}</main>
      </div>
    </>
  )
}
