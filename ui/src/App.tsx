import { useEffect } from 'react'
import { Board } from '@/components/app/Board'
import { ClockBar } from '@/components/app/ClockBar'
import { AlertsFeed } from '@/components/app/AlertsFeed'
import { DealDetail } from '@/components/app/DealDetail'
import { ErrorBoundary } from '@/components/app/ErrorBoundary'
import { Inbox } from '@/components/app/Inbox'
import { useInbox } from './data/queries.ts'
import { buildHash } from './route.ts'
import type { Route } from './route.ts'
import { useClockStore } from './state/clockStore.ts'
import { useAnswersStore } from './state/answersStore.ts'
import { useUiStore } from './state/uiStore.ts'
import { inboxAt, pendingCount, simToMs } from './time/timeview.ts'

// The rail lists only views that exist (D-11): Pipeline, Inbox with its pending count, and Alerts.
const NAV_ITEMS: { id: Route['view']; label: string; route: Route }[] = [
  { id: 'pipeline', label: 'Pipeline', route: { view: 'pipeline' } },
  { id: 'inbox', label: 'Inbox', route: { view: 'inbox' } },
  { id: 'alerts', label: 'Alerts', route: { view: 'alerts' } },
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
  const status = useClockStore((s) => s.status)
  const now = useClockStore((s) => s.now)
  const answers = useAnswersStore((s) => s.answers)
  const inbox = useInbox()
  // Pending at the clock time, session answers applied; a number only once the inbox has loaded.
  const pending =
    status === 'ready' && inbox.data !== undefined ? pendingCount(inboxAt(inbox.data, simToMs(now), answers)) : null
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
                  className={`flex h-10 items-center justify-between border-l-4 px-4 text-sm focus-visible:outline-sky ${
                    active
                      ? 'border-sky bg-surface/10 font-bold text-surface'
                      : 'border-transparent font-medium text-surface/75 hover:bg-surface/5 hover:text-surface'
                  }`}
                >
                  {item.label}
                  {item.id === 'inbox' && pending !== null && (
                    <span className="rounded-sm bg-sky px-1.5 text-xs font-bold tabular-nums text-navy" aria-label={`${pending} pending`}>
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
    const title = PAGE_TITLES[route.view]
    if (title !== undefined) document.title = title
  }, [route])

  return (
    <>
      <ClockBar />
      <div className="flex">
        <Rail />
        <main className="flex min-w-0 flex-1 flex-col gap-4 p-6">
          <ErrorBoundary resetKey={buildHash(route)}>
            {status === 'ready' && route.view === 'deal' && <DealDetail key={route.folder} folder={route.folder} />}
            {status === 'ready' && route.view === 'pipeline' && <Board />}
            {status === 'ready' && route.view === 'inbox' && <Inbox />}
            {status === 'ready' && route.view === 'alerts' && <AlertsFeed />}
          </ErrorBoundary>
        </main>
      </div>
    </>
  )
}
