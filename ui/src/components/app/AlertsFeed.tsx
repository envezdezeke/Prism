import { useEffect } from 'react'
import { describeError } from '../../api/client.ts'
import type { AlertFeedItem } from '../../api/types.ts'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { useAlerts } from '../../data/queries.ts'
import { fmtSimTime } from '../../lib/format.ts'
import { alertLevelLabel } from '../../labels.ts'
import { personLabel, roleForAlert } from '../../people.ts'
import { useClockStore } from '../../state/clockStore.ts'
import { alertsAt, simToMs } from '../../time/timeview.ts'
import { DealLink, EmptyState, ErrorState, LoadingState, PageTitle } from './Primitives.tsx'

// Newest first, only what has fired by the clock time. Escalations (150% and 200%) carry an amber edge.
export function AlertsFeedView({ alerts, now }: { alerts: AlertFeedItem[]; now: string }) {
  const visible = alertsAt(alerts, simToMs(now), 'newest')
  return (
    <section aria-label="Alerts" className="flex flex-col gap-4">
      <PageTitle>Alerts</PageTitle>
      {visible.length === 0 ? (
        <EmptyState heading="No alerts yet.">
          Alerts fire at 100% of a stage's limit and escalate at 150% and 200%. None had fired as of {fmtSimTime(now)}.
        </EmptyState>
      ) : (
        <div className="rounded-md border border-line bg-surface">
          <Table>
            <TableHeader className="bg-navy [&_th]:text-xs [&_th]:font-bold [&_th]:tracking-wide [&_th]:text-surface [&_th]:uppercase">
              <TableRow className="border-navy hover:bg-transparent">
                <TableHead className="border-l-2 border-transparent">Time</TableHead>
                <TableHead>Level</TableHead>
                <TableHead>Deal</TableHead>
                <TableHead>Stage</TableHead>
                <TableHead>To</TableHead>
                <TableHead>Message</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {visible.map((a) => {
                const who = personLabel(a.to, roleForAlert(a.level))
                const edge = a.level === 'escalation' ? 'border-risk' : 'border-transparent'
                return (
                  <TableRow key={a.id} className="animate-fade-in align-top">
                    <TableCell className={`whitespace-nowrap border-l-2 tabular-nums ${edge}`}>{fmtSimTime(a.at)}</TableCell>
                    <TableCell className={`whitespace-nowrap ${a.level === 'escalation' ? 'font-semibold text-risk' : ''}`}>
                      {alertLevelLabel(a.level, a.message)}
                    </TableCell>
                    <TableCell className="whitespace-nowrap">
                      <DealLink folder={a.deal}>{a.deal}</DealLink>
                    </TableCell>
                    <TableCell className="whitespace-nowrap">{a.stage}</TableCell>
                    <TableCell className="whitespace-nowrap" title={who.title}>
                      {who.label}
                    </TableCell>
                    <TableCell className="whitespace-normal">{a.message}</TableCell>
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

export function AlertsFeed() {
  const now = useClockStore((s) => s.now)
  const q = useAlerts()
  useEffect(() => {
    document.title = 'Alerts · Prism'
  }, [])
  if (q.isPending) return <LoadingState>Loading alerts.</LoadingState>
  if (q.isError) return <ErrorState heading="Could not load alerts." message={describeError(q.error)} onRetry={() => void q.refetch()} />
  return <AlertsFeedView alerts={q.data} now={now} />
}
