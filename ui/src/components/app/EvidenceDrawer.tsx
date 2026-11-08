import { useState } from 'react'
import type { ReactNode } from 'react'
import { describeError } from '../../api/client.ts'
import type { TraceStep } from '../../api/types.ts'
import { Badge } from '@/components/ui/badge'
import { useInvestigator } from '../../data/queries.ts'
import { edgesOfNode, sharersOf } from '../../graph/graphview.ts'
import type { GCluster, GEdge, GraphView } from '../../graph/graphview.ts'
import { fmtSimTime } from '../../lib/format.ts'
import { FAMILIES, entityKindLabel, rarityText } from '../../labels.ts'
import type { Selection } from './GraphCanvas.tsx'
import { Caption, DealLink, LoadingState } from './Primitives.tsx'

type Tab = 'evidence' | 'investigator'

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="flex flex-col gap-2 border-t border-line pt-4">
      <h3 className="text-xs font-semibold text-ink-2">{title}</h3>
      {children}
    </section>
  )
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-4">
      <dt className="text-xs font-semibold text-ink-2">{label}</dt>
      <dd className="min-w-0 text-right text-sm tabular-nums">{children}</dd>
    </div>
  )
}

// A rarity bar: 0 to 1, full width is the rarest. Neutral fill, red only on a lit ring edge.
function RarityBar({ value, lit }: { value: number; lit: boolean }) {
  return (
    <div role="img" aria-label={rarityText(value)} className="h-0.5 w-full bg-line">
      <div className={`h-full ${lit ? 'bg-hold' : 'bg-ink-2'}`} style={{ width: `${Math.round(value * 100)}%` }} />
    </div>
  )
}

function NodeName({ id, boardFolders, nodeLabel }: { id: string; boardFolders: string[]; nodeLabel: (id: string) => string }) {
  return boardFolders.includes(id) ? <DealLink folder={id}>{nodeLabel(id)}</DealLink> : <span>{nodeLabel(id)}</span>
}

// The six families in plain words, fired first in contract order. Evidence is the engine's sentence.
export function FamilyList({ cluster }: { cluster: GCluster }) {
  const fired = FAMILIES.filter((f) => cluster.families[f.id]?.fired)
  return (
    <div className="flex flex-col gap-2">
      <p className="text-sm">
        <span className="font-semibold tabular-nums">{fired.length} of 6</span> families fired
      </p>
      <ul className="flex flex-col gap-2">
        {FAMILIES.map((f) => {
          const r = cluster.families[f.id]
          const on = r?.fired === true
          return (
            <li key={f.id} className="flex flex-col gap-0.5">
              <span className={`text-sm ${on ? 'font-semibold text-ink' : 'text-ink-2'}`}>
                {f.id} {f.label}
                <span className="font-normal text-ink-2"> · {on ? 'fired' : 'not fired'}</span>
              </span>
              {on && r && <span className="text-xs text-ink-2">{r.evidence}</span>}
            </li>
          )
        })}
      </ul>
    </div>
  )
}

function EdgeEvidence({
  edge,
  view,
  ringHeld,
  boardFolders,
  nodeLabel,
  onSelect,
}: {
  edge: GEdge
  view: GraphView
  ringHeld: boolean
  boardFolders: string[]
  nodeLabel: (id: string) => string
  onSelect: (s: Selection) => void
}) {
  const lit = view.ringEdges.has(edge) && ringHeld
  const sharers = sharersOf(view, edge.target)
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-1">
        <Caption>Shared {entityKindLabel(edge.entity_kind).toLowerCase()}</Caption>
        <p className="text-base font-semibold">{nodeLabel(edge.target)}</p>
      </div>
      <p className="text-base">{edge.evidence}</p>
      <dl className="flex flex-col gap-2">
        <Field label="Deal">
          <NodeName id={edge.source} boardFolders={boardFolders} nodeLabel={nodeLabel} />
        </Field>
        <Field label="Rarity">{edge.rarity.toFixed(2)}</Field>
        <Field label="Weight">{edge.weight.toFixed(2)}</Field>
        <Field label="Visible from">{fmtSimTime(edge.first_visible_at)}</Field>
      </dl>
      <RarityBar value={edge.rarity} lit={lit} />
      <Section title={`Shared by ${sharers.length} ${sharers.length === 1 ? 'deal' : 'deals'} as of now`}>
        <ul className="flex flex-col gap-1">
          {sharers.map((e) => (
            <li key={e.source}>
              <button
                type="button"
                onClick={() => onSelect({ kind: 'edge', edge: e })}
                className="flex w-full items-baseline justify-between gap-2 rounded-sm px-1 text-left text-sm hover:bg-subtle"
              >
                <span className="truncate">{nodeLabel(e.source)}</span>
                <span className="shrink-0 text-xs text-ink-2 tabular-nums">{fmtSimTime(e.first_visible_at)}</span>
              </button>
            </li>
          ))}
        </ul>
      </Section>
    </div>
  )
}

function NodeEvidence({
  id,
  view,
  ringDeals,
  ringHeld,
  boardFolders,
  nodeLabel,
  onSelect,
}: {
  id: string
  view: GraphView
  ringDeals: Set<string>
  ringHeld: boolean
  boardFolders: string[]
  nodeLabel: (id: string) => string
  onSelect: (s: Selection) => void
}) {
  const node = view.nodes.find((n) => n.id === id)
  if (!node) return <p className="text-sm text-ink-2">This node is not visible at the current time.</p>
  const edges = edgesOfNode(view, id)
  const isEntity = node.type === 'entity'
  const status = isEntity
    ? null
    : ringDeals.has(id)
      ? ringHeld
        ? 'In the held ring'
        : 'In the ring, not held yet at this time'
      : view.focus.has(id)
        ? 'One hop from the ring. Not held'
        : 'Not linked to this ring. Not held'
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-1">
        <Caption>{isEntity ? entityKindLabel(node.kind) : node.type === 'history_deal' ? 'Prior deal (history)' : 'Deal'}</Caption>
        <p className="text-base font-semibold">{node.label}</p>
        {status !== null && <p className="text-sm text-ink-2">{status}</p>}
        {boardFolders.includes(id) && (
          <p className="text-sm">
            <DealLink folder={id}>Open deal</DealLink>
          </p>
        )}
      </div>
      <Section title={isEntity ? `Shared by ${edges.length} ${edges.length === 1 ? 'deal' : 'deals'}` : `${edges.length} shared values`}>
        {edges.length === 0 ? (
          <p className="text-sm text-ink-2">No shared values as of now.</p>
        ) : (
          <ul className="flex flex-col gap-1">
            {edges.map((e) => (
              <li key={`${e.source}-${e.target}`}>
                <button
                  type="button"
                  onClick={() => onSelect({ kind: 'edge', edge: e })}
                  className="flex w-full items-baseline justify-between gap-2 rounded-sm px-1 text-left text-sm hover:bg-subtle"
                >
                  <span className="truncate">
                    {isEntity ? nodeLabel(e.source) : `${entityKindLabel(e.entity_kind)}: ${nodeLabel(e.target)}`}
                  </span>
                  <span className={`shrink-0 text-xs tabular-nums ${view.ringEdges.has(e) && ringHeld ? 'text-hold' : 'text-ink-2'}`}>
                    {e.rarity.toFixed(2)}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </Section>
    </div>
  )
}

const argText = (v: unknown): string => (Array.isArray(v) ? v.map(String).join(', ') : typeof v === 'object' && v !== null ? JSON.stringify(v) : String(v))

function StepItem({ s }: { s: TraceStep }) {
  return (
    <li className="flex flex-col gap-1 border-l border-line pl-3">
      <div className="flex items-baseline gap-2">
        <span className="text-xs font-semibold text-ink-2 tabular-nums">Step {s.step}</span>
        <Badge variant="chip">{s.tool}</Badge>
      </div>
      <p className="text-sm text-ink-2">{s.thought}</p>
      {Object.keys(s.args).length > 0 && (
        <dl className="flex flex-col gap-0.5">
          {Object.entries(s.args).map(([k, v]) => (
            <div key={k} className="flex gap-2 text-xs">
              <dt className="font-semibold text-ink-2">{k}</dt>
              <dd className="min-w-0 break-words text-ink">{argText(v)}</dd>
            </div>
          ))}
        </dl>
      )}
      <p className="text-sm">{s.result_summary}</p>
    </li>
  )
}

function InvestigatorPanel({ clusterId }: { clusterId: string }) {
  const q = useInvestigator(clusterId)
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-2 rounded-sm border border-line p-3">
        <div className="flex items-center gap-2">
          <Badge variant="outline">Advisory</Badge>
          <span className="text-xs text-ink-2">Investigator agent{q.data ? ` · ${q.data.mode}` : ''}</span>
        </div>
        <p className="text-xs text-ink-2">
          The agent explains the case. It does not decide it: the hold comes from the deterministic families on the Evidence tab.
        </p>
      </div>
      {q.isPending ? (
        <LoadingState>Loading the investigator trace.</LoadingState>
      ) : q.isError ? (
        <p className="text-sm text-ink-2">
          {(q.error as { status?: number }).status === 404 ? 'No investigator trace for this cluster.' : describeError(q.error)}
        </p>
      ) : (
        <>
          <ol className="flex flex-col gap-4">
            {q.data.steps.map((s) => (
              <StepItem key={s.step} s={s} />
            ))}
          </ol>
          <Section title="Case summary (advisory)">
            <p className="text-sm">{q.data.case_summary}</p>
          </Section>
        </>
      )}
    </div>
  )
}

export function EvidenceDrawer({
  selection,
  cluster,
  view,
  ringDeals,
  ringHeld,
  boardFolders,
  nodeLabel,
  onSelect,
}: {
  selection: Selection
  cluster: GCluster | null
  view: GraphView
  ringDeals: Set<string>
  ringHeld: boolean
  boardFolders: string[]
  nodeLabel: (id: string) => string
  onSelect: (s: Selection) => void
}) {
  const [tab, setTab] = useState<Tab>('evidence')
  const tabClass = (t: Tab): string =>
    `-mb-px border-b-2 px-1 pb-2 text-sm ${tab === t ? 'border-navy font-semibold text-navy' : 'border-transparent text-ink-2 hover:text-ink'}`
  const selKey = selection === null ? 'none' : selection.kind === 'edge' ? `e:${selection.edge.source}:${selection.edge.target}` : `n:${selection.id}`

  return (
    <aside aria-label="Evidence" className="flex w-80 shrink-0 flex-col gap-4 overflow-y-auto rounded-md border border-line bg-surface p-4">
      <div role="tablist" aria-label="Drawer" className="flex gap-4 border-b border-line">
        <button type="button" role="tab" aria-selected={tab === 'evidence'} className={tabClass('evidence')} onClick={() => setTab('evidence')}>
          Evidence
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === 'investigator'}
          className={tabClass('investigator')}
          onClick={() => setTab('investigator')}
          disabled={cluster === null}
        >
          Investigator
        </button>
      </div>
      <div key={`${tab}-${selKey}`} className="flex animate-drawer-in flex-col gap-4">
        {tab === 'investigator' && cluster !== null ? (
          <InvestigatorPanel clusterId={cluster.id} />
        ) : (
          <>
            {selection === null && (
              <p className="text-sm text-ink-2">Select an edge or a node to see the shared value, its rarity and the source sentence.</p>
            )}
            {selection?.kind === 'edge' && (
              <EdgeEvidence edge={selection.edge} view={view} ringHeld={ringHeld} boardFolders={boardFolders} nodeLabel={nodeLabel} onSelect={onSelect} />
            )}
            {selection?.kind === 'node' && (
              <NodeEvidence
                id={selection.id}
                view={view}
                ringDeals={ringDeals}
                ringHeld={ringHeld}
                boardFolders={boardFolders}
                nodeLabel={nodeLabel}
                onSelect={onSelect}
              />
            )}
            {cluster !== null && (
              <Section title={`Cluster ${cluster.id} · families`}>
                <FamilyList cluster={cluster} />
              </Section>
            )}
          </>
        )}
      </div>
    </aside>
  )
}
