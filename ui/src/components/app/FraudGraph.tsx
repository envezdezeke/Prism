import { useEffect, useLayoutEffect, useMemo, useState } from 'react'
import { describeError } from '../../api/client.ts'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useDealDetails, useDeals, useGraph, useRedteam } from '../../data/queries.ts'
import { clusterHoldAt, defaultClusterId, graphAt, redteamTotals } from '../../graph/graphview.ts'
import type { GGraph } from '../../graph/graphview.ts'
import { readPalette } from '../../graph/palette.ts'
import type { GraphPalette } from '../../graph/palette.ts'
import { fmtSimTime } from '../../lib/format.ts'
import { buildHash } from '../../route.ts'
import { useClockStore } from '../../state/clockStore.ts'
import { simToMs } from '../../time/timeview.ts'
import { EvidenceDrawer } from './EvidenceDrawer.tsx'
import { GraphCanvas } from './GraphCanvas.tsx'
import type { Selection } from './GraphCanvas.tsx'
import { Caption, ErrorState, LoadingState, PageTitle, PipelineLink } from './Primitives.tsx'

// Investigation mode (D-25): the dark tokens apply to the whole frame while this screen is mounted.
// Set in a layout effect so the canvas palette is read after the switch, and removed on the way out.
function useInvestigationMode(): GraphPalette | null {
  const [palette, setPalette] = useState<GraphPalette | null>(null)
  useLayoutEffect(() => {
    const root = document.documentElement
    root.dataset.view = 'investigate'
    setPalette(readPalette(root))
    return () => {
      delete root.dataset.view
    }
  }, [])
  return palette
}

function Legend() {
  const item = 'flex items-center gap-2'
  return (
    <ul aria-label="Legend" className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink-2">
      <li className={item}>
        <span aria-hidden="true" className="size-2.5 rounded-full bg-graph-deal" />
        Deal
      </li>
      <li className={item}>
        <span aria-hidden="true" className="size-2.5 rounded-full border-2 border-graph-history" />
        Prior deal
      </li>
      <li className={item}>
        <span aria-hidden="true" className="size-2 bg-graph-document" />
        Document party
      </li>
      <li className={item}>
        <span aria-hidden="true" className="size-2 bg-graph-identity" />
        Identity
      </li>
      <li className={item}>
        <span aria-hidden="true" className="size-2 bg-graph-money" />
        Money
      </li>
      <li className={item}>
        <span aria-hidden="true" className="h-0.5 w-4 bg-hold" />
        Held ring (rare shared value)
      </li>
    </ul>
  )
}

export function FraudGraphView({
  graph,
  clusterId,
  palette,
}: {
  graph: GGraph
  clusterId: string | null
  palette: GraphPalette | null
}) {
  const now = useClockStore((s) => s.now)
  const deals = useDeals()
  const boardFolders = useMemo(() => (deals.data ?? []).map((d) => d.folder), [deals.data])
  const { details } = useDealDetails(boardFolders)
  const redteam = useRedteam()
  const [selection, setSelection] = useState<Selection>(null)
  const [fitMode, setFitMode] = useState<'focus' | 'all'>('focus')
  const [fitToken, setFitToken] = useState(0)

  const activeId = clusterId ?? defaultClusterId(graph)
  const cluster = graph.clusters.find((c) => c.id === activeId) ?? null
  const nowMs = simToMs(now)
  const view = useMemo(() => graphAt(graph, details, nowMs, cluster), [graph, details, nowMs, cluster])
  const hold = cluster ? clusterHoldAt(cluster, details, nowMs) : { held: false, at: null }
  const ringDeals = useMemo(() => new Set(cluster?.deals ?? []), [cluster])
  const labels = useMemo(() => new Map(graph.nodes.map((n) => [n.id, n.label])), [graph])
  const nodeLabel = (id: string): string => labels.get(id) ?? id

  useEffect(() => {
    document.title = 'Fraud graph · Prism'
  }, [])

  if (cluster === null && graph.clusters.length > 0 && clusterId !== null) {
    return (
      <ErrorState heading="This cluster is not in the run." message={`No cluster with id ${clusterId}.`} />
    )
  }

  const rt = redteam.data ? redteamTotals(redteam.data.tricks) : null
  const ringVisible = cluster?.deals.filter((d) => view.nodes.some((n) => n.id === d)) ?? []

  return (
    <div className="flex flex-col gap-4">
      <nav aria-label="Breadcrumb" className="text-xs text-ink-2">
        <PipelineLink>Pipeline</PipelineLink>
        <span> / Fraud graph</span>
      </nav>
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="flex flex-col gap-2">
          <PageTitle>{cluster ? `Ring ${cluster.id}` : 'Fraud graph'}</PageTitle>
          {cluster && (
            <div className="flex flex-wrap items-center gap-2">
              {hold.held ? (
                <span key="held" className="animate-fade-in">
                  <Badge variant="hold">Held: fraud review</Badge>
                </span>
              ) : (
                <Badge variant="outline">{cluster.tier === 'watch' ? 'Watch' : cluster.tier === 'hold' ? 'Forming: not held yet' : 'No flag'}</Badge>
              )}
              <span className="text-sm text-ink-2">
                {hold.held && hold.at
                  ? `Held since ${fmtSimTime(hold.at)} · ${ringVisible.length} of ${cluster.deals.length} ring deals on screen`
                  : `${ringVisible.length} of ${cluster.deals.length} ring deals on screen as of ${fmtSimTime(now)}`}
              </span>
              {rt && (
                <Badge variant="chip" title={`${rt.falseFlags} false ${rt.falseFlags === 1 ? 'flag' : 'flags'} across the synthetic tricks`}>
                  Red-team: {rt.bypasses} {rt.bypasses === 1 ? 'bypass' : 'bypasses'} / {rt.attempts} attempts
                </Badge>
              )}
            </div>
          )}
        </div>
        {graph.clusters.length > 1 && (
          <nav aria-label="Clusters" className="flex gap-2">
            {graph.clusters.map((c) => (
              <a
                key={c.id}
                href={buildHash({ view: 'graph', clusterId: c.id })}
                aria-current={c.id === activeId ? 'page' : undefined}
                className={`rounded-sm border px-2 py-1 text-xs ${
                  c.id === activeId ? 'border-navy font-semibold text-navy' : 'border-line text-ink-2 hover:bg-subtle'
                }`}
              >
                {c.id} · {c.tier}
              </a>
            ))}
          </nav>
        )}
      </header>

      <div className="flex h-[calc(100vh-14rem)] min-h-[32rem] gap-4">
        <div className="relative min-w-0 flex-1 overflow-hidden rounded-md border border-line bg-page">
          {palette && (
            <GraphCanvas
              view={view}
              ringDeals={ringDeals}
              ringHeld={hold.held}
              palette={palette}
              selection={selection}
              onSelect={setSelection}
              fitMode={fitMode}
              fitToken={fitToken}
            />
          )}
          <div className="pointer-events-none absolute inset-x-0 top-0 flex items-start justify-between gap-4 p-3">
            <Caption>
              {view.edges.length} shared values visible as of {fmtSimTime(now)}. Replay the clock to watch the ring form.
            </Caption>
            <div className="pointer-events-auto flex gap-2">
              <Button
                variant={fitMode === 'focus' ? 'default' : 'outline'}
                size="sm"
                onClick={() => {
                  setFitMode('focus')
                  setFitToken((n) => n + 1)
                }}
              >
                Focus ring
              </Button>
              <Button
                variant={fitMode === 'all' ? 'default' : 'outline'}
                size="sm"
                onClick={() => {
                  setFitMode('all')
                  setFitToken((n) => n + 1)
                }}
              >
                Whole graph
              </Button>
            </div>
          </div>
          <div className="pointer-events-none absolute inset-x-0 bottom-0 flex flex-col gap-2 p-3">
            {view.backgroundDeals.length > 0 && (
              <p className="text-sm text-ink">
                <span className="font-semibold tabular-nums">{view.backgroundDeals.length}</span>{' '}
                {view.backgroundDeals.length === 1 ? 'deal is' : 'deals are'} outside this ring: not linked, not held.{' '}
                <span className="text-ink-2">{view.backgroundDeals.map(nodeLabel).join(', ')}</span>
              </p>
            )}
            <Legend />
          </div>
        </div>
        <EvidenceDrawer
          selection={selection}
          cluster={cluster}
          view={view}
          ringDeals={ringDeals}
          ringHeld={hold.held}
          boardFolders={boardFolders}
          nodeLabel={nodeLabel}
          onSelect={setSelection}
        />
      </div>
    </div>
  )
}

export function FraudGraph({ clusterId }: { clusterId: string | null }) {
  const palette = useInvestigationMode()
  const g = useGraph()
  if (g.isPending) return <LoadingState>Loading the fraud graph.</LoadingState>
  if (g.isError) {
    return <ErrorState heading="Could not load the fraud graph." message={describeError(g.error)} onRetry={() => void g.refetch()} />
  }
  if (g.data.nodes.length === 0) {
    return <Caption>No deals in the graph yet.</Caption>
  }
  // Keyed by cluster: switching clusters starts with a clean drawer and a fresh fit.
  return <FraudGraphView key={clusterId ?? ''} graph={g.data as GGraph} clusterId={clusterId} palette={palette} />
}
