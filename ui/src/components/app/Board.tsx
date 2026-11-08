import { useMemo } from 'react'
import { describeError } from '../../api/client.ts'
import { STAGES } from '../../api/types.ts'
import type { DealDetail, Stage } from '../../api/types.ts'
import { useDealDetails, useDeals } from '../../data/queries.ts'
import { fmtHours, fmtMoney, fmtPct, fmtSimTime, fmtSla } from '../../lib/format.ts'
import { useClockStore } from '../../state/clockStore.ts'
import { boardAt, simToMs, sortBoardRows } from '../../time/timeview.ts'
import type { BoardRow } from '../../time/timeview.ts'
import { NeededByBadge, SlaBar, StatusBadge } from './Badges.tsx'
import { Caption, DealLink, EmptyState, ErrorState, LoadingState, NullValue, PageTitle } from './Primitives.tsx'
import { Button } from '@/components/ui/button'

function DealCard({ row }: { row: BoardRow<DealDetail> }) {
  const { deal } = row
  const name = deal.legal_name ?? deal.folder
  // Amber follows the displayed value: above 100 percent once rounded.
  const over = Math.round(row.slaFraction * 100) > 100
  const showFolder = deal.legal_name != null && deal.legal_name !== deal.folder
  const slaText = fmtSla(row.slaFraction, deal.sla_hours)
  return (
    <li>
      <DealLink
        folder={deal.folder}
        className="flex flex-col gap-1 rounded-md border border-line bg-surface px-3 py-2 text-ink transition-colors duration-150 hover:bg-subtle"
      >
        <div className="flex items-start justify-between gap-2">
          <span className="line-clamp-2 min-w-0 text-sm font-semibold" title={name}>
            {name}
          </span>
          <span className="shrink-0 text-right text-sm tabular-nums">
            {deal.amount_requested == null ? <NullValue /> : fmtMoney(deal.amount_requested)}
          </span>
        </div>
        {showFolder && (
          <span className="truncate text-xs text-ink-2" title={deal.folder}>
            {deal.folder}
          </span>
        )}
        <div className="flex flex-wrap items-start gap-1">
          <StatusBadge
            held={row.held}
            watch={deal.watch}
            reason={row.held ? deal.fraud.reason : null}
            cleared={row.stage === 'Closed'}
          />
          <NeededByBadge badge={deal.needed_by_badge} neededBy={deal.needed_by ?? null} />
        </div>
        <span
          className={`text-xs tabular-nums ${over ? 'text-risk' : 'text-ink-2'}`}
          title={row.held ? 'SLA clock stopped at the hold' : undefined}
        >
          {slaText}
        </span>
        <SlaBar pct={row.slaFraction} label={`SLA ${fmtPct(row.slaFraction)} of the stage limit`} />
      </DealLink>
    </li>
  )
}

// The stage limit is shown only when every deal in the column shares it (UI-SPEC row 8).
function stageLimit(col: BoardRow<DealDetail>[]): string | null {
  if (col.length === 0) return null
  const first = col[0].deal.sla_hours
  return col.every((r) => r.deal.sla_hours === first) ? fmtHours(first) : null
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
  const sorted = sortBoardRows(rows)
  const byStage = (stage: Stage) => sorted.filter((r) => r.stage === stage)

  return (
    <section aria-label="Pipeline board" className="flex flex-col gap-2">
      <PageTitle>Pipeline</PageTitle>
      <Caption>
        {rows.length} {rows.length === 1 ? 'deal' : 'deals'} as of {when} · As of end of run: amount, needed-by and Watch
      </Caption>
      {failedCount > 0 && (
        <p className="text-sm text-ink">
          {failedCount} {failedCount === 1 ? 'deal' : 'deals'} could not be loaded.{' '}
          <Button variant="link" size="sm" className="h-auto px-0" onClick={onRetryFailed}>
            Retry
          </Button>
        </p>
      )}
      {rows.length === 0 && (
        <EmptyState heading="No deals have arrived yet.">
          No deals have arrived as of {when}. Advance the clock to bring files in.
        </EmptyState>
      )}
      <div className="overflow-x-auto">
        <div className="grid grid-cols-[repeat(6,minmax(10rem,1fr))] gap-2">
          {STAGES.map((stage) => {
            const col = byStage(stage)
            const limit = stageLimit(col)
            return (
              <div key={stage} className="flex min-w-0 flex-col gap-2 bg-page">
                <h2 className="flex items-baseline justify-between gap-2 text-xs font-semibold text-ink-2">
                  <span>{stage}</span>
                  <span className="font-normal tabular-nums">
                    {col.length}
                    {limit ? ` · ${limit}` : ''}
                  </span>
                </h2>
                {col.length === 0 ? (
                  <Caption>
                    No deals in {stage} as of {when}.
                  </Caption>
                ) : (
                  <ul className="flex max-h-[70vh] flex-col gap-2 overflow-y-auto">
                    {col.map((r) => (
                      <DealCard key={r.deal.folder} row={r} />
                    ))}
                  </ul>
                )}
              </div>
            )
          })}
        </div>
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

  if (deals.isPending) return <LoadingState>Loading deals.</LoadingState>
  if (deals.isError) {
    return (
      <ErrorState heading="Could not load deals." message={describeError(deals.error)} onRetry={() => void deals.refetch()} />
    )
  }
  return (
    <>
      {isLoading && <LoadingState>Loading deals.</LoadingState>}
      <BoardView rows={rows} now={now} failedCount={errors.length} onRetryFailed={refetchFailed} />
    </>
  )
}
