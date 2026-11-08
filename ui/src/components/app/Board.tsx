import { useMemo } from 'react'
import { CircleAlert } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { describeError } from '../../api/client.ts'
import { STAGES } from '../../api/types.ts'
import type { DealDetail, Stage } from '../../api/types.ts'
import { useDealDetails, useDeals } from '../../data/queries.ts'
import { fmtMoney, fmtSimTime } from '../../lib/format.ts'
import { useClockStore } from '../../state/clockStore.ts'
import { boardAt, roundPct, simToMs } from '../../time/timeview.ts'
import type { BoardRow } from '../../time/timeview.ts'

// Whole-number SLA percent from the raw fraction (the same rounding that reproduces the API's sla_pct).
const wholePct = (fraction: number): number => Math.round(roundPct(fraction) * 100)

function StatusLine({ children }: { children: string }) {
  return <p className="text-sm text-ink-2">{children}</p>
}

// Neutral on purpose: red is reserved for a fraud hold (D-05, D-20).
function ErrorBlock({ heading, body, onRetry }: { heading: string; body: string; onRetry: () => void }) {
  return (
    <div role="alert" className="flex items-start gap-2 rounded-md border border-line bg-surface p-4 text-ink">
      <CircleAlert className="mt-0.5 size-4 shrink-0 text-ink-2" aria-hidden="true" />
      <div className="flex flex-col gap-2">
        <p className="text-base font-semibold">{heading}</p>
        <p className="text-sm">{body}</p>
        <div>
          <Button variant="outline" size="sm" onClick={onRetry}>
            Retry
          </Button>
        </div>
      </div>
    </div>
  )
}

function DealCard({ row }: { row: BoardRow<DealDetail> }) {
  const { deal } = row
  const name = deal.legal_name ?? deal.folder
  const pct = wholePct(row.slaFraction)
  return (
    <li className="flex flex-col gap-1 rounded-md border border-line bg-surface px-3 py-2">
      <div className="flex items-start justify-between gap-2">
        <span className="line-clamp-2 text-sm font-semibold">{name}</span>
        <span className="shrink-0 text-sm">
          {deal.amount_requested == null ? <span className="text-tertiary">—</span> : fmtMoney(deal.amount_requested)}
        </span>
      </div>
      {deal.legal_name != null && deal.legal_name !== deal.folder && (
        <span className="truncate text-xs text-ink-2">{deal.folder}</span>
      )}
      <span className={pct > 100 ? 'text-xs text-risk' : 'text-xs text-ink-2'}>SLA {pct}%</span>
      {row.held && (
        <div>
          <Badge variant="hold">Held: fraud review</Badge>
        </div>
      )}
    </li>
  )
}

export function BoardView({
  rows,
  now,
  failedCount,
  onRetryFailed,
}: {
  rows: BoardRow<DealDetail>[]
  now: string
  failedCount: number
  onRetryFailed: () => void
}) {
  const when = fmtSimTime(now)
  const byStage = (stage: Stage) =>
    rows
      .filter((r) => r.stage === stage)
      // Held deals first; otherwise keep the API's order.
      .sort((a, b) => Number(b.held) - Number(a.held))

  return (
    <section aria-label="Pipeline board" className="flex flex-col gap-2">
      <p className="text-xs text-ink-2">
        {rows.length} {rows.length === 1 ? 'deal' : 'deals'} as of {when} · Amounts as of end of run
      </p>
      {failedCount > 0 && (
        <p className="text-sm text-ink">
          {failedCount} {failedCount === 1 ? 'deal' : 'deals'} could not be loaded.{' '}
          <Button variant="link" size="sm" className="h-auto px-0" onClick={onRetryFailed}>
            Retry
          </Button>
        </p>
      )}
      {rows.length === 0 && (
        <div className="rounded-md border border-line bg-surface p-4">
          <p className="text-base font-semibold">No deals have arrived yet.</p>
          <p className="text-sm text-ink-2">No deals have arrived as of {when}. Advance the clock to bring files in.</p>
        </div>
      )}
      <div className="grid grid-cols-6 gap-2">
        {STAGES.map((stage) => {
          const col = byStage(stage)
          return (
            <div key={stage} className="flex min-w-40 flex-col gap-2 bg-page">
              <h2 className="flex items-baseline justify-between text-xs font-semibold text-ink-2">
                <span>{stage}</span>
                <span className="font-normal">{col.length}</span>
              </h2>
              {col.length === 0 ? (
                <p className="text-xs text-ink-2">
                  No deals in {stage} as of {when}.
                </p>
              ) : (
                <ul className="flex flex-col gap-2">
                  {col.map((r) => (
                    <DealCard key={r.deal.folder} row={r} />
                  ))}
                </ul>
              )}
            </div>
          )
        })}
      </div>
    </section>
  )
}

export function Board() {
  const now = useClockStore((s) => s.now)
  const deals = useDeals()
  const folders = useMemo(() => (deals.data ?? []).map((d) => d.folder), [deals.data])
  const { details, isLoading, errors, refetchFailed } = useDealDetails(folders)

  const rows = useMemo(() => boardAt(details, simToMs(now)), [details, now])

  if (deals.isPending) return <StatusLine>Loading deals.</StatusLine>
  if (deals.isError) {
    return <ErrorBlock heading="Could not load deals." body={describeError(deals.error)} onRetry={() => void deals.refetch()} />
  }
  return (
    <>
      {isLoading && <StatusLine>Loading deals.</StatusLine>}
      <BoardView rows={rows} now={now} failedCount={errors.length} onRetryFailed={refetchFailed} />
    </>
  )
}
