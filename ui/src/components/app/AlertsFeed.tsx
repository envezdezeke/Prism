import { useMemo } from 'react'
import { describeError } from '../../api/client.ts'
import type { AlertFeedItem } from '../../api/types.ts'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { useAlerts, useDeals } from '../../data/queries.ts'
import { fmtSimTime } from '../../lib/format.ts'
import { alertLevelLabel } from '../../labels.ts'
import { personLabel, roleForAlert } from '../../people.ts'
import { useClockStore } from '../../state/clockStore.ts'
import { alertsAt, simToMs } from '../../time/timeview.ts'
import { Caption, DealLink, EmptyState, ErrorState, LoadingState, PageTitle } from './Primitives.tsx'

export function AlertsView({
  alerts,
  names,
  now,
}: {
  alerts: AlertFeedItem[]
  names: Map<string, string | null>
  now: string
}) {
  const visible = alertsAt(alerts, simToMs(now), 'newest')
  if (visible.length === 0) {
    return (
      <EmptyState heading="No alerts yet.">
        Alerts fire at 100% of a stage's limit and escalate at 150% and 200%. None had fired as of {fmtSimTime(now)}.
      </EmptyState>
    )
  }
  return (
    <div className="rounded-md border border-line bg-surface">
      <Table>
        <TableHeader className="bg-navy [&_th]:text-xs [&_th]:font-bold [&_th]:tracking-wide [&_th]:text-surface [&_th]:uppercase">
          <TableRow className="border-navy hover:bg-transparent">
            <TableHead className="border-l-4 border-transparent">Time</TableHead>
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
            const legal = names.get(a.deal)
            const showFolder = legal != null && legal !== a.deal
            // Amber marks escalations only; nothing else in the feed is coloured.
            const edge = a.level === 'escalation' ? 'border-risk' : 'border-transparent'
            return (
              <TableRow key={a.id} className="align-top">
                <TableCell className={`border-l-4 whitespace-nowrap font-semibold tabular-nums ${edge}`}>{fmtSimTime(a.at)}</TableCell>
                <TableCell className="whitespace-nowrap font-semibold text-navy">{alertLevelLabel(a.level, a.message)}</TableCell>
                <TableCell className="max-w-48">
                  <DealLink folder={a.deal}>
                    <span className="block truncate font-semibold" title={legal ?? a.deal}>
                      {legal ?? a.deal}
                    </span>
                  </DealLink>
                  {showFolder && (
                    <span className="block truncate text-xs text-ink-2" title={a.deal}>
                      {a.deal}
                    </span>
                  )}
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
  )
}

export function AlertsFeed() {
  const now = useClockStore((s) => s.now)
  const q = useAlerts()
  const deals = useDeals()
  const names = useMemo(() => new Map((deals.data ?? []).map((d) => [d.folder, d.legal_name ?? null])), [deals.data])

  return (
    <div className="flex flex-col gap-4">
      <PageTitle>Alerts</PageTitle>
      <Caption>Newest first. Only alerts sent by the clock time are shown.</Caption>
      {q.isPending ? (
        <LoadingState>Loading alerts.</LoadingState>
      ) : q.isError ? (
        <ErrorState heading="Could not load alerts." message={describeError(q.error)} onRetry={() => void q.refetch()} />
      ) : (
        <AlertsView alerts={q.data} names={names} now={now} />
      )}
    </div>
  )
}
