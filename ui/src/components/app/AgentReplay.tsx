import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { FileSearch, FileText, History, Network, Pause, Play, RotateCcw, SkipForward, Sparkles, Users, X } from 'lucide-react'
import type { InvestigatorTrace, TraceStep } from '../../api/types.ts'
import type { GEdge, GNode } from '../../graph/graphview.ts'
import type { GraphControls } from './GraphCanvas.tsx'

// Playback of a recorded Nemotron investigator trace over the fraud graph. Display only: the
// deterministic engine made the hold; nothing here changes a scored output.

type Pt = { x: number; y: number }
type Phase = 'travel' | 'scan' | 'collect' | 'done'

interface ToolLook {
  color: string
  label: string
  icon: typeof Network
  say: (target: string) => string
}

const TOOLS: Record<string, ToolLook> = {
  cluster_summary: { color: 'var(--color-agent-cluster)', label: 'Cluster summary', icon: Network, say: () => 'Sizing up the whole ring first…' },
  deal_entities: { color: 'var(--color-agent-entities)', label: 'Parties & accounts', icon: Users, say: (t) => `Pulling every party and account on ${t}…` },
  entity_deals: { color: 'var(--color-agent-reach)', label: 'Who else uses it', icon: FileSearch, say: (t) => `Checking who else uses “${t}”…` },
  deal_documents: { color: 'var(--color-agent-docs)', label: 'Documents', icon: FileText, say: (t) => `Reading the documents filed for ${t}…` },
  history_deal: { color: 'var(--color-agent-history)', label: 'Loan history', icon: History, say: (t) => `Looking up prior loan ${t} in the history book…` },
}
// Older trace tool names (the mock fixture) map onto the same looks.
TOOLS.graph_neighbors = { ...TOOLS.entity_deals, label: 'Graph neighbours', say: (t) => `Following every shared link out of ${t}…` }
TOOLS.history_search = TOOLS.history_deal
TOOLS.doc_forensics = { ...TOOLS.deal_documents, label: 'Document forensics', say: (t) => `Comparing how ${t} was produced…` }
TOOLS.deposit_pattern = { color: 'var(--color-agent-other)', label: 'Deposit pattern', icon: Sparkles, say: () => 'Scanning deposit history for a staged pattern…' }
const FALLBACK: ToolLook = { color: 'var(--color-agent-other)', label: 'Lookup', icon: Sparkles, say: (t) => `Looking into ${t}…` }
const mix = (c: string, pct: number): string => `color-mix(in srgb, ${c} ${pct}%, transparent)`
const look = (tool: string): ToolLook => TOOLS[tool] ?? FALLBACK

const MS = { travel: 1100, scan: 1500, collect: 700 }

const norm = (s: string): string => s.toLowerCase().split(/\s+/).filter(Boolean).sort().join(' ')

export function resolveTargets(step: TraceStep, nodes: GNode[], clusterDeals: string[]): { ids: string[]; name: string } {
  const a = step.args as Record<string, unknown>
  const str = (k: string): string | null => (typeof a[k] === 'string' ? (a[k] as string) : null)
  const byName = (v: string): GNode | undefined => {
    const l = v.toLowerCase()
    return nodes.find((n) => n.id.toLowerCase() === l || n.label.toLowerCase() === l)
  }
  const kind = str('kind')
  const value = str('value')
  if (value) {
    const nv = norm(value)
    const hit = nodes.find((n) => n.type === 'entity' && (!kind || n.kind === kind) && norm(n.label) === nv)
    if (hit) return { ids: [hit.id], name: value }
  }
  for (const k of ['deal', 'deal_id', 'entity', 'doc']) {
    const v = str(k)
    const hit = v ? byName(v) : undefined
    if (hit) return { ids: [hit.id], name: hit.label }
  }
  const present = clusterDeals.filter((d) => nodes.some((n) => n.id === d))
  const name = str('cluster_id') ?? str('deal') ?? value ?? 'the ring'
  return { ids: present, name }
}

function neighbours(ids: string[], edges: GEdge[]): string[] {
  const set = new Set(ids)
  const out: string[] = []
  for (const e of edges) {
    if (set.has(e.source) && !set.has(e.target)) out.push(e.target)
    else if (set.has(e.target) && !set.has(e.source)) out.push(e.source)
    if (out.length >= 10) break
  }
  return [...new Set(out)]
}

function centroid(pts: Pt[]): Pt | null {
  if (pts.length === 0) return null
  return { x: pts.reduce((s, p) => s + p.x, 0) / pts.length, y: pts.reduce((s, p) => s + p.y, 0) / pts.length }
}

interface Card {
  step: number
  tool: string
  name: string
  text: string
}

function Cursor({ at, color, trail }: { at: Pt; color: string; trail: Pt[] }) {
  return (
    <>
      {trail.map((p, i) => (
        <span
          key={i}
          aria-hidden="true"
          className="absolute rounded-full"
          style={{
            left: p.x - 3,
            top: p.y - 3,
            width: 6,
            height: 6,
            background: color,
            opacity: ((i + 1) / trail.length) * 0.35,
          }}
        />
      ))}
      <div aria-hidden="true" className="absolute" style={{ left: at.x, top: at.y, transition: 'filter 300ms' }}>
        <svg width="26" height="26" viewBox="0 0 24 24" >
          <path d="M3 2 L20 11 L12 13 L9 21 Z" fill={color} stroke="white" strokeWidth="1.6" strokeLinejoin="round" />
        </svg>
        <span
          className="absolute left-5 top-5 rounded-full px-2 py-0.5 text-[11px] font-semibold whitespace-nowrap text-white shadow-sm"
          style={{ background: color, transition: 'background 300ms' }}
        >
          Nemotron
        </span>
      </div>
    </>
  )
}

function useTyped(text: string, active: boolean, cps = 70): string {
  const [n, setN] = useState(0)
  useEffect(() => {
    setN(0)
    if (!active) return
    const id = window.setInterval(() => setN((k) => (k >= text.length ? k : k + 2)), 1000 / cps)
    return () => window.clearInterval(id)
  }, [text, active, cps])
  return active ? text.slice(0, n) : ''
}

export function AgentReplay({
  trace,
  nodes,
  edges,
  clusterDeals,
  controls,
  onClose,
}: {
  trace: InvestigatorTrace
  nodes: GNode[]
  edges: GEdge[]
  clusterDeals: string[]
  controls: React.MutableRefObject<GraphControls | null>
  onClose: () => void
}) {
  const wrap = useRef<HTMLDivElement>(null)
  const caseFile = useRef<HTMLOListElement>(null)
  const [stepIdx, setStepIdx] = useState(0)
  const [phase, setPhase] = useState<Phase>('travel')
  const [playing, setPlaying] = useState(true)
  const [speed, setSpeed] = useState(1)
  const [cards, setCards] = useState<Card[]>([])
  const [cursor, setCursor] = useState<Pt>({ x: 40, y: 40 })
  const [trail, setTrail] = useState<Pt[]>([])
  const [targetPts, setTargetPts] = useState<Pt[]>([])
  const [neighPts, setNeighPts] = useState<{ from: Pt; to: Pt }[]>([])
  const [flyer, setFlyer] = useState<{ from: Pt; to: Pt; go: boolean } | null>(null)
  const cursorRef = useRef(cursor)

  const steps = trace.steps
  const step = steps[Math.min(stepIdx, steps.length - 1)]
  const tl = look(step?.tool ?? '')
  const target = useMemo(
    () => (step ? resolveTargets(step, nodes, clusterDeals) : { ids: [], name: '' }),
    [step, nodes, clusterDeals],
  )
  const neigh = useMemo(() => neighbours(target.ids, edges), [target, edges])

  // Frame the nodes of each step.
  useEffect(() => {
    if (phase !== 'travel' || target.ids.length === 0) return
    controls.current?.focusOn(new Set([...target.ids, ...neigh]), 900 / speed)
  }, [stepIdx, phase, target, neigh, controls, speed])

  // Animation loop: follow the target's live screen position (the graph can move under us).
  useEffect(() => {
    let raf = 0
    const tick = (): void => {
      const c = controls.current
      if (c) {
        const tp = target.ids.map((id) => c.screenPos(id)).filter((p): p is Pt => p !== null)
        setTargetPts(tp)
        const firstOf = new Map(target.ids.map((id) => [id, c.screenPos(id)]))
        const np: { from: Pt; to: Pt }[] = []
        for (const e of edges) {
          const tgtIn = firstOf.has(e.source) ? e.source : firstOf.has(e.target) ? e.target : null
          if (!tgtIn) continue
          const other = tgtIn === e.source ? e.target : e.source
          if (!neigh.includes(other)) continue
          const a = firstOf.get(tgtIn)
          const b = c.screenPos(other)
          if (a && b) np.push({ from: a, to: b })
        }
        setNeighPts(np)
        const goal = centroid(tp)
        if (goal && phase !== 'done') {
          const cur = cursorRef.current
          const k = phase === 'travel' ? 0.09 * speed : 0.2
          const next = { x: cur.x + (goal.x - cur.x) * Math.min(k, 1), y: cur.y + (goal.y - cur.y) * Math.min(k, 1) }
          cursorRef.current = next
          setCursor(next)
          setTrail((t) => [...t.slice(-11), next])
        }
      }
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [controls, target, neigh, edges, phase, speed])

  // Step clock: travel -> scan -> collect -> next step.
  useEffect(() => {
    if (!playing || phase === 'done') return
    const t = window.setTimeout(() => {
      if (phase === 'travel') setPhase('scan')
      else if (phase === 'scan') {
        const box = caseFile.current?.getBoundingClientRect()
        const host = wrap.current?.getBoundingClientRect()
        const to = box && host ? { x: box.left - host.left + 8, y: box.top - host.top + 8 } : { x: 0, y: 0 }
        setFlyer({ from: cursorRef.current, to, go: false })
        setPhase('collect')
      } else if (phase === 'collect') {
        setFlyer(null)
        setCards((cs) => [{ step: step.step, tool: step.tool, name: target.name, text: step.result_summary }, ...cs])
        if (stepIdx + 1 >= steps.length) setPhase('done')
        else {
          setStepIdx((i) => i + 1)
          setPhase('travel')
        }
      }
    }, MS[phase] / speed)
    return () => window.clearTimeout(t)
  }, [playing, phase, speed, stepIdx, steps.length, step, target])

  // Launch the flying card on the frame after it mounts so the transition runs.
  useLayoutEffect(() => {
    if (flyer && !flyer.go) requestAnimationFrame(() => setFlyer((f) => (f ? { ...f, go: true } : f)))
  }, [flyer])

  useEffect(() => {
    if (phase === 'done') controls.current?.focusOn(new Set(clusterDeals), 900)
  }, [phase, controls, clusterDeals])

  const typed = useTyped(step?.result_summary ?? '', phase === 'scan' || phase === 'collect')
  const restart = (): void => {
    setCards([])
    setStepIdx(0)
    setPhase('travel')
    setPlaying(true)
  }
  const skip = (): void => {
    if (phase === 'done') return
    setFlyer(null)
    setCards((cs) => [{ step: step.step, tool: step.tool, name: target.name, text: step.result_summary }, ...cs])
    if (stepIdx + 1 >= steps.length) setPhase('done')
    else {
      setStepIdx((i) => i + 1)
      setPhase('travel')
    }
  }

  const Icon = tl.icon
  const hostW = wrap.current?.clientWidth ?? 1000
  const hostH = wrap.current?.clientHeight ?? 700
  // Keep the bubble clear of the case file column (288px + gutter) on the right.
  const flip = cursor.x + 30 + 288 > hostW - 300
  const scanning = phase === 'scan' || phase === 'collect'

  return (
    <div ref={wrap} className="pointer-events-none absolute inset-0 z-10" aria-live="polite">
      
      <svg className="absolute inset-0 h-full w-full overflow-visible">
        {scanning &&
          neighPts.map((l, i) => (
            <line
              key={`n${i}`}
              x1={l.from.x}
              y1={l.from.y}
              x2={l.to.x}
              y2={l.to.y}
              stroke={tl.color}
              strokeWidth={2.5}
              strokeLinecap="round"
              strokeDasharray="6 6"
              opacity={0.85}
            >
              <animate attributeName="stroke-dashoffset" from="24" to="0" dur="0.6s" repeatCount="indefinite" />
            </line>
          ))}
        {scanning &&
          neighPts.map((l, i) => (
            <circle key={`nc${i}`} cx={l.to.x} cy={l.to.y} r={9} fill="none" stroke={tl.color} strokeWidth={2} opacity={0.7}>
              <animate attributeName="r" values="6;12;6" dur="1.2s" begin={`${i * 0.12}s`} repeatCount="indefinite" />
            </circle>
          ))}
        {phase !== 'done' &&
          targetPts.map((p, i) => (
            <line
              key={`t${i}`}
              x1={cursor.x}
              y1={cursor.y}
              x2={p.x}
              y2={p.y}
              stroke={tl.color}
              strokeWidth={1.5}
              strokeDasharray="3 5"
              opacity={0.6}
            />
          ))}
        {targetPts.map((p, i) => (
          <g key={`r${i}`}>
            <circle cx={p.x} cy={p.y} r={26} fill={mix(tl.color, 8)} stroke={tl.color} strokeWidth={2.5} strokeDasharray="10 7">
              <animateTransform attributeName="transform" type="rotate" from={`0 ${p.x} ${p.y}`} to={`360 ${p.x} ${p.y}`} dur="3s" repeatCount="indefinite" />
            </circle>
            {scanning && (
              <circle cx={p.x} cy={p.y} r={26} fill="none" stroke={tl.color} strokeWidth={2}>
                <animate attributeName="r" from="26" to="70" dur="1.1s" repeatCount="indefinite" />
                <animate attributeName="opacity" from="0.8" to="0" dur="1.1s" repeatCount="indefinite" />
              </circle>
            )}
          </g>
        ))}
      </svg>

      {phase !== 'done' && <Cursor at={cursor} color={tl.color} trail={trail} />}


      {/* Evidence card in flight to the case file. */}
      {flyer && (
        <div
          className="absolute w-56 rounded-md border bg-surface px-2 py-1.5 text-[11px] shadow-sm"
          style={{
            left: 0,
            top: 0,
            borderColor: tl.color,
            transform: `translate(${(flyer.go ? flyer.to : flyer.from).x}px, ${(flyer.go ? flyer.to : flyer.from).y}px) scale(${flyer.go ? 0.9 : 1.05})`,
            transition: `transform ${MS.collect * 0.9 / speed}ms cubic-bezier(.5,0,.2,1)`,
          }}
        >
          <span className="font-semibold" style={{ color: tl.color }}>
            {tl.label}
          </span>{' '}
          · {target.name}
        </div>
      )}

      {/* Header strip: who is working, progress, controls. */}
      <div className="pointer-events-auto absolute inset-x-3 top-3 flex items-center gap-3 rounded-lg border border-line bg-surface px-3 py-2 shadow-sm ">
        <span className="relative flex size-2.5">
          {phase !== 'done' && playing && <span className="absolute inline-flex size-full animate-ping rounded-full opacity-75" style={{ background: tl.color }} />}
          <span className="relative inline-flex size-2.5 rounded-full" style={{ background: phase === 'done' ? 'var(--color-agent-done)' : tl.color }} />
        </span>
        <div className="min-w-0">
          <p className="text-sm font-semibold text-ink">
            {phase === 'done' ? 'Nemotron finished the investigation' : `Nemotron is investigating ${trace.cluster_id}`}
          </p>
          <p className="text-[11px] text-ink-2">
            {trace.mode === 'off' ? 'Template trace (Nemotron off)' : 'Replay of a recorded Nemotron run'} · advisory only, the engine made the hold
          </p>
        </div>
        <ol className="ml-2 flex flex-1 items-center gap-1" aria-label="Steps">
          {steps.map((s, i) => (
            <li
              key={i}
              title={`${s.step}. ${s.tool}`}
              className="h-1.5 flex-1 rounded-full transition-all duration-500"
              style={{
                background: i < stepIdx || phase === 'done' ? look(s.tool).color : i === stepIdx ? mix(look(s.tool).color, 55) : 'var(--color-line)',
                transform: i === stepIdx && phase !== 'done' ? 'scaleY(1.8)' : 'none',
              }}
            />
          ))}
        </ol>
        <span className="text-xs text-ink-2 tabular-nums">
          {Math.min(stepIdx + 1, steps.length)}/{steps.length}
        </span>
        <div className="flex items-center gap-1">
          <IconBtn label={playing ? 'Pause' : 'Play'} onClick={() => setPlaying((p) => !p)} disabled={phase === 'done'}>
            {playing ? <Pause className="size-3.5" /> : <Play className="size-3.5" />}
          </IconBtn>
          <IconBtn label="Next step" onClick={skip} disabled={phase === 'done'}>
            <SkipForward className="size-3.5" />
          </IconBtn>
          <IconBtn label="Replay" onClick={restart}>
            <RotateCcw className="size-3.5" />
          </IconBtn>
          <button
            type="button"
            onClick={() => setSpeed((s) => (s === 1 ? 2 : 1))}
            className="h-7 rounded-md border border-line px-2 text-xs font-medium text-ink-2 hover:bg-subtle"
          >
            {speed}×
          </button>
          <IconBtn label="Close" onClick={onClose}>
            <X className="size-3.5" />
          </IconBtn>
        </div>
      </div>

      {/* Case file: evidence the agent has collected so far. */}
      <div className="pointer-events-auto absolute right-3 top-20 bottom-3 flex w-64 flex-col rounded-lg border border-line bg-surface shadow-sm ">
        <p className="border-b border-line px-3 py-2 text-xs font-semibold text-ink">
          Case file <span className="font-normal text-ink-2">· {cards.length} findings</span>
        </p>
        <ol ref={caseFile} className="flex-1 space-y-2 overflow-y-auto p-2">
          {cards.map((c) => {
            const l = look(c.tool)
            const CIcon = l.icon
            return (
              <li
                key={`${c.step}-${c.tool}`}
                className="animate-fade-in rounded-md border-l-4 bg-subtle px-2 py-1.5 text-[11px] leading-snug text-ink"
                style={{ borderColor: l.color }}
              >
                <span className="mb-0.5 flex items-center gap-1 font-semibold" style={{ color: l.color }}>
                  <CIcon className="size-3" aria-hidden="true" />
                  {c.step}. {l.label}
                </span>
                {c.text}
              </li>
            )
          })}
        </ol>
        {phase === 'done' && (
          <div className="animate-fade-in border-t border-line p-3">
            <p className="mb-1 flex items-center gap-1 text-xs font-semibold text-ink">
              <Sparkles className="size-3.5" aria-hidden="true" /> Case summary
            </p>
            <p className="text-xs leading-relaxed text-ink">{trace.case_summary}</p>
          </div>
        )}
      </div>
      {/* Thought bubble next to the cursor. */}
      {phase !== 'done' && step && (
        <div
          className="absolute z-20 w-72 rounded-lg border bg-surface p-3 text-xs shadow-sm "
          style={{ left: flip ? Math.max(8, cursor.x - 300) : cursor.x + 30, top: Math.min(Math.max(80, cursor.y + 34), hostH - 160), borderColor: mix(tl.color, 40), transition: 'border-color 300ms' }}
        >
          <div className="mb-1 flex items-center gap-1.5 font-semibold" style={{ color: tl.color }}>
            <Icon className="size-3.5" aria-hidden="true" />
            {tl.label}
            <code className="ml-auto rounded bg-subtle px-1 font-mono text-[10px] text-ink-2">{step.tool}()</code>
          </div>
          <p className="text-ink">{tl.say(target.name)}</p>
          {scanning && (
            <p className="mt-1.5 border-t border-line pt-1.5 font-mono text-[11px] text-ink-2">
              {typed}
              <span className="ml-0.5 inline-block h-3 w-1.5 animate-pulse align-middle" style={{ background: tl.color }} />
            </p>
          )}
        </div>
      )}
    </div>
  )
}

function IconBtn({ label, onClick, disabled, children }: { label: string; onClick: () => void; disabled?: boolean; children: React.ReactNode }) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      onClick={onClick}
      disabled={disabled}
      className="inline-flex size-7 items-center justify-center rounded-md border border-line text-ink hover:bg-subtle disabled:opacity-40"
    >
      {children}
    </button>
  )
}
