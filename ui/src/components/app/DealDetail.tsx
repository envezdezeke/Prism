import { useEffect } from 'react'
import { describeError } from '../../api/client.ts'
import type { DealDetail as DealDetailData, Fact } from '../../api/types.ts'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { useDealDetail } from '../../data/queries.ts'
import { fmtDuration, fmtHours, fmtMoney, fmtPct, fmtSimTime } from '../../lib/format.ts'
import { factFields, factValueText } from '../../labels.ts'
import { personLabel } from '../../people.ts'
import { useClockStore } from '../../state/clockStore.ts'
import { useUiStore } from '../../state/uiStore.ts'
import { boardAt, simToMs } from '../../time/timeview.ts'
import type { BoardRow } from '../../time/timeview.ts'
import { StatusBadge } from './Badges.tsx'
import { Caption, EmptyState, ErrorState, LoadingState, NullValue, PageTitle, PipelineLink } from './Primitives.tsx'

const HOUR_MS = 3600_000

function Breadcrumb({ name }: { name: string | null }) {
  return (
    <nav aria-label="Breadcrumb" className="text-xs text-ink-2">
      <PipelineLink>Pipeline</PipelineLink>
      {name !== null && <span> / {name}</span>}
    </nav>
  )
}

function Row({ label, children, title }: { label: string; children: React.ReactNode; title?: string }) {
  return (
    <div className="flex items-baseline justify-between gap-4">
      <dt className="text-xs font-semibold text-ink-2">{label}</dt>
      <dd className="min-w-0 text-right text-sm tabular-nums" title={title}>
        {children}
      </dd>
    </div>
  )
}

// Side panel. Stage, time in stage and SLA follow the clock; the rows below the caption are static (D-18).
function SummaryPanel({ row }: { row: BoardRow<DealDetailData> }) {
  const { deal } = row
  const over = Math.round(row.slaFraction * 100) > 100
  const rm = deal.rm == null ? null : personLabel(deal.rm, 'Relationship manager')
  return (
    <section aria-label="Summary" className="flex flex-col gap-2 rounded-md border border-line bg-surface p-4">
      <h2 className="text-base font-semibold">Summary</h2>
      <dl className="flex flex-col gap-2">
        <Row label="Stage">{row.stage}</Row>
        <Row label="Stage entered">{fmtSimTime(row.enteredAt)}</Row>
        <Row label="Time in stage">{fmtDuration(row.slaFraction * deal.sla_hours * HOUR_MS)}</Row>
        <Row label="SLA" title={row.held ? 'SLA clock stopped at the hold' : undefined}>
          <span className={over ? 'text-risk' : undefined}>
            {fmtPct(row.slaFraction)} of {fmtHours(deal.sla_hours)}
          </span>
        </Row>
      </dl>
      <Caption>As of end of run</Caption>
      <dl className="flex flex-col gap-2">
        <Row label="Needed by" title={deal.needed_by == null ? undefined : fmtSimTime(deal.needed_by)}>
          {deal.needed_by == null ? (
            <NullValue title="No date in the documents" />
          ) : (
            <>
              {fmtSimTime(deal.needed_by)}
              {deal.needed_by_badge === 'at_risk' && <span className="font-semibold text-risk"> · At risk</span>}
              {deal.needed_by_badge === 'overdue' && <span className="font-semibold text-risk"> · Overdue</span>}
            </>
          )}
        </Row>
        <Row label="Amount requested">{deal.amount_requested == null ? <NullValue /> : fmtMoney(deal.amount_requested)}</Row>
        <Row label="Relationship manager" title={rm?.title}>
          {rm === null ? <NullValue /> : rm.label}
        </Row>
      </dl>
    </section>
  )
}

function FactsSection({ deal }: { deal: DealDetailData }) {
  const facts = deal.facts as unknown as Record<string, Fact | null | undefined>
  const anyFact = factFields.some((f) => facts[f.key] != null)
  return (
    <section aria-label="Facts" className="flex flex-col gap-2">
      <div className="flex items-baseline gap-2">
        <h2 className="text-base font-semibold">Facts</h2>
        <Caption>As of end of run</Caption>
      </div>
      {!anyFact ? (
        <EmptyState>No facts were extracted for this deal.</EmptyState>
      ) : (
        <div className="rounded-md border border-line bg-surface">
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead>Field</TableHead>
                <TableHead>Value</TableHead>
                <TableHead>Source</TableHead>
                <TableHead>Confidence</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {factFields.map(({ key, label }) => {
                const fact = facts[key]
                const money = key === 'amount_requested' || key === 'annual_revenue_stated'
                return (
                  <TableRow key={key}>
                    <TableCell className="text-xs font-semibold text-ink-2">{label}</TableCell>
                    {fact == null ? (
                      <>
                        <TableCell>
                          <NullValue />
                        </TableCell>
                        <TableCell>
                          <NullValue />
                        </TableCell>
                        <TableCell>
                          <NullValue />
                        </TableCell>
                      </>
                    ) : (
                      <>
                        <TableCell className={`tabular-nums${money ? ' text-right' : ''}`}>
                          {factValueText(key, fact.value)}
                        </TableCell>
                        <TableCell>
                          <Badge variant="chip">{fact.source_doc}</Badge>
                        </TableCell>
                        <TableCell className="tabular-nums">{fmtPct(fact.confidence)}</TableCell>
                      </>
                    )}
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </div>
      )}
    </section>
  )
}

// The screen as a pure function of (fetched detail, clock now): the same boardAt the board uses decides
// the stage, SLA and held state, so the two screens agree at every clock time and one clock change
// can never show a mixed state.
export function DealDetailView({ detail, now }: { detail: DealDetailData; now: string }) {
  const name = detail.legal_name ?? detail.folder
  const row = boardAt([detail], simToMs(now))[0]
  const showFolder = detail.legal_name != null && detail.legal_name !== detail.folder

  if (row === undefined) {
    return (
      <div className="flex flex-col gap-4">
        <Breadcrumb name={name} />
        <EmptyState heading={`${name} has not arrived as of ${fmtSimTime(now)}.`}>
          <PipelineLink>Back to pipeline</PipelineLink>
        </EmptyState>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4">
      <Breadcrumb name={name} />
      <header className="flex flex-col gap-1">
        <PageTitle>{name}</PageTitle>
        {showFolder && <p className="text-sm text-ink-2">{detail.folder}</p>}
        <div className="flex flex-wrap items-center gap-2 pt-1">
          <Badge variant="secondary">{row.stage}</Badge>
          <StatusBadge
            held={row.held}
            watch={detail.watch}
            reason={row.held ? detail.fraud.reason : null}
            cleared={row.stage === 'Closed'}
          />
        </div>
      </header>
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <div className="flex min-w-0 flex-col gap-8">
          <FactsSection deal={detail} />
        </div>
        <div className="flex flex-col gap-4 lg:sticky lg:top-6 lg:self-start">
          <SummaryPanel row={row} />
        </div>
      </div>
    </div>
  )
}

export function DealDetail({ folder }: { folder: string }) {
  const now = useClockStore((s) => s.now)
  const showPipeline = useUiStore((s) => s.showPipeline)
  const q = useDealDetail(folder)
  const name = q.data ? (q.data.legal_name ?? q.data.folder) : null

  useEffect(() => {
    document.title = `${name ?? folder} · Prism`
  }, [name, folder])

  if (q.isPending) {
    return (
      <div className="flex flex-col gap-4">
        <Breadcrumb name={null} />
        <LoadingState>Loading deal.</LoadingState>
      </div>
    )
  }
  if (q.isError) {
    return (
      <div className="flex flex-col gap-4">
        <Breadcrumb name={null} />
        <ErrorState heading="Could not load this deal." message={describeError(q.error)} onRetry={() => void q.refetch()} />
        <div>
          <Button variant="outline" size="sm" onClick={showPipeline}>
            Back to pipeline
          </Button>
        </div>
      </div>
    )
  }
  return <DealDetailView detail={q.data} now={now} />
}
