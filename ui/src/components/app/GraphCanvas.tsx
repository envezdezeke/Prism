import { useEffect, useMemo, useRef, useState } from 'react'
import ForceGraph2D from 'react-force-graph-2d'
import type { ForceGraphMethods, LinkObject, NodeObject } from 'react-force-graph-2d'
import { edgeKey, kindGroup } from '../../graph/graphview.ts'
import type { GEdge, GNode, GraphView } from '../../graph/graphview.ts'
import type { GraphPalette } from '../../graph/palette.ts'
import { withAlpha } from '../../graph/palette.ts'
import { LayoutCache } from '../../graph/layoutCache.ts'
import { entityKindLabel } from '../../labels.ts'

export type Selection = { kind: 'edge'; edge: GEdge } | { kind: 'node'; id: string } | null

interface NodeData {
  id: string
  node: GNode
}
interface LinkData {
  key: string
  edge: GEdge
}
type N = NodeObject<NodeData>
type L = LinkObject<NodeData, LinkData>

// Canvas sizes in screen pixels; divided by the zoom so text stays legible on a projector.
const LABEL_PX = 13
const EDGE_LABEL_PX = 12
const DEAL_R = 7
const ENTITY_SIDE = 8
// A new edge fades in over this many real milliseconds when the clock reveals it (D-29).
const FADE_MS = 600
// Canvas-only halo on ring elements (D-30). Never applied to anything else.
const HALO = 14
const GRAVITY = 0.03
// Text keeps a fixed screen size when zoomed in, and shrinks with the graph when zoomed out.
const textScale = (scale: number): number => Math.max(scale, 1)

const endId = (v: L['source']): string => (typeof v === 'object' && v !== null ? String(v.id) : String(v))

export function GraphCanvas({
  view,
  ringDeals,
  ringHeld,
  palette,
  selection,
  onSelect,
  fitMode,
  fitToken,
}: {
  view: GraphView
  ringDeals: Set<string>
  ringHeld: boolean
  palette: GraphPalette
  selection: Selection
  onSelect: (s: Selection) => void
  fitMode: 'focus' | 'all'
  fitToken: number
}) {
  const wrapRef = useRef<HTMLDivElement>(null)
  const fgRef = useRef<ForceGraphMethods<N, L> | undefined>(undefined)
  const [size, setSize] = useState({ w: 0, h: 0 })
  // Stable objects keep the force layout from jumping between clock ticks.
  const [cache] = useState(() => new LayoutCache())
  const data = useMemo(() => cache.sync(view) as { nodes: N[]; links: L[] }, [cache, view])
  const needsFit = useRef(true)
  // New nodes from the clock: refit once the layout settles so nothing grows off the canvas.
  useEffect(() => {
    needsFit.current = true
  }, [view.nodes.length])

  useEffect(() => {
    const el = wrapRef.current
    if (!el) return
    const ro = new ResizeObserver(([entry]) => {
      setSize({ w: Math.floor(entry.contentRect.width), h: Math.floor(entry.contentRect.height) })
    })
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  useEffect(() => {
    const fg = fgRef.current
    if (!fg) return
    fg.d3Force('charge')?.strength(-320)
    fg.d3Force('link')?.distance(80)
    // Gentle pull to the centre so unlinked deals stay near the ring instead of drifting off-screen.
    let nodes: N[] = []
    const gravity = Object.assign(
      (alpha: number) => {
        for (const n of nodes) {
          n.vx = (n.vx ?? 0) - (n.x ?? 0) * GRAVITY * alpha
          n.vy = (n.vy ?? 0) - (n.y ?? 0) * GRAVITY * alpha
        }
      },
      { initialize: (ns: N[]) => (nodes = ns) },
    )
    fg.d3Force('gravity', gravity)
    fg.d3ReheatSimulation()
  }, [size.w])

  // The latest view and mode, read by the fit (called from an effect and from onEngineStop).
  const fitState = useRef({ view, fitMode })
  useEffect(() => {
    fitState.current = { view, fitMode }
  })
  const fit = (fg: ForceGraphMethods<N, L>): void => {
    const { view: v, fitMode: mode } = fitState.current
    const filter = mode === 'focus' && v.focus.size > 0 ? (n: N) => v.focus.has(String(n.id)) : undefined
    fg.zoomToFit(600, 128, filter)
  }

  useEffect(() => {
    needsFit.current = true
    const fg = fgRef.current
    if (!fg) return
    const { view: v, fitMode: mode } = fitState.current
    const filter = mode === 'focus' && v.focus.size > 0 ? (n: N) => v.focus.has(String(n.id)) : undefined
    fg.zoomToFit(600, 128, filter)
  }, [fitToken, fitMode])

  const selectedNode = selection?.kind === 'node' ? selection.id : null
  const selectedEdge = selection?.kind === 'edge' ? edgeKey(selection.edge) : null
  const p = palette

  const fadeAlpha = (key: string): number => cache.fade(key, performance.now(), FADE_MS)

  const drawNode = (obj: N, ctx: CanvasRenderingContext2D, scale: number): void => {
    const n = obj.node
    const x = obj.x ?? 0
    const y = obj.y ?? 0
    const inFocus = view.focus.has(n.id)
    const inRing = ringDeals.has(n.id) || view.ringEntities.has(n.id)
    const lit = inRing && ringHeld
    const alpha = inFocus ? 1 : 0.28
    ctx.save()
    if (lit) {
      ctx.shadowColor = p.hold
      ctx.shadowBlur = HALO
    }
    if (n.type === 'entity') {
      const s = ENTITY_SIDE
      const tint = p[kindGroup(n.kind)]
      ctx.fillStyle = withAlpha(tint, alpha)
      ctx.fillRect(x - s / 2, y - s / 2, s, s)
      if (lit) {
        ctx.strokeStyle = p.hold
        ctx.lineWidth = 1.5
        ctx.strokeRect(x - s / 2, y - s / 2, s, s)
      }
    } else if (n.type === 'history_deal') {
      ctx.beginPath()
      ctx.arc(x, y, DEAL_R, 0, 2 * Math.PI)
      ctx.strokeStyle = withAlpha(lit ? p.hold : p.history, alpha)
      ctx.lineWidth = 2
      ctx.stroke()
    } else {
      ctx.beginPath()
      ctx.arc(x, y, DEAL_R, 0, 2 * Math.PI)
      ctx.fillStyle = withAlpha(lit ? p.hold : p.deal, alpha)
      ctx.fill()
      if (inRing && !ringHeld) {
        ctx.strokeStyle = p.navy
        ctx.lineWidth = 1.5
        ctx.stroke()
      }
    }
    ctx.restore()

    if (selectedNode === n.id) {
      ctx.beginPath()
      ctx.arc(x, y, DEAL_R + 5, 0, 2 * Math.PI)
      ctx.strokeStyle = p.navy
      ctx.lineWidth = 2 / scale
      ctx.stroke()
    }

    // Labels: deals always; entities show their value and kind, in the focus only.
    if (n.type === 'entity' && !inFocus) return
    const fs = LABEL_PX / textScale(scale)
    ctx.textAlign = 'center'
    ctx.textBaseline = 'top'
    ctx.font = `${n.type === 'entity' ? 400 : 600} ${fs}px 'Geist Variable', ui-sans-serif, sans-serif`
    ctx.fillStyle = withAlpha(lit ? p.ink : n.type === 'entity' ? p.ink2 : p.ink, inFocus ? 1 : 0.4)
    const top = y + (n.type === 'entity' ? ENTITY_SIDE / 2 : DEAL_R) + 4 / textScale(scale)
    ctx.fillText(n.label, x, top)
    if (n.type === 'entity' && inFocus) {
      ctx.font = `400 ${(LABEL_PX - 1) / textScale(scale)}px 'Geist Variable', ui-sans-serif, sans-serif`
      ctx.fillStyle = withAlpha(p.ink2, 0.9)
      ctx.fillText(entityKindLabel(n.kind), x, top + fs * 1.25)
    }
  }

  const paintNodeArea = (obj: N, color: string, ctx: CanvasRenderingContext2D): void => {
    ctx.fillStyle = color
    ctx.beginPath()
    ctx.arc(obj.x ?? 0, obj.y ?? 0, DEAL_R + 4, 0, 2 * Math.PI)
    ctx.fill()
  }

  const drawLink = (obj: L, ctx: CanvasRenderingContext2D, scale: number): void => {
    const s = obj.source as N
    const t = obj.target as N
    if (typeof s !== 'object' || typeof t !== 'object') return
    const e = obj.edge
    const sx = s.x ?? 0
    const sy = s.y ?? 0
    const tx = t.x ?? 0
    const ty = t.y ?? 0
    const inFocus = view.focus.has(endId(obj.source)) && view.focus.has(endId(obj.target))
    const ring = view.ringEdges.has(e)
    const lit = ring && ringHeld
    const fade = fadeAlpha(obj.key)
    const base = inFocus ? 0.35 + 0.65 * e.rarity : 0.12
    const selected = selectedEdge === obj.key

    ctx.save()
    ctx.beginPath()
    ctx.moveTo(sx, sy)
    ctx.lineTo(tx, ty)
    // Weight drives thickness (contract). Kept in screen pixels so zoom does not bloat it.
    ctx.lineWidth = (0.75 + e.weight * 0.9) / scale
    if (lit) {
      ctx.shadowColor = p.hold
      ctx.shadowBlur = HALO
      ctx.strokeStyle = withAlpha(p.hold, fade)
    } else if (ring) {
      ctx.strokeStyle = withAlpha(p.navy, 0.85 * fade)
    } else {
      ctx.strokeStyle = withAlpha(inFocus ? p.ink2 : p.edge, base * fade)
    }
    ctx.stroke()
    if (selected) {
      ctx.shadowBlur = 0
      ctx.lineWidth = (3 + e.weight * 0.9) / scale
      ctx.strokeStyle = withAlpha(p.navy, 0.6)
      ctx.stroke()
    }
    ctx.restore()

    // Edge label: shared kind and rarity, focus edges only (D-28).
    if (inFocus && fade > 0.5 && (scale >= 1.2 || selected)) {
      const label = `${entityKindLabel(e.entity_kind).toLowerCase()} · ${e.rarity.toFixed(2)}`
      const fs = EDGE_LABEL_PX / textScale(scale)
      ctx.font = `400 ${fs}px 'Geist Variable', ui-sans-serif, sans-serif`
      const mx = (sx + tx) / 2
      const my = (sy + ty) / 2
      const w = ctx.measureText(label).width + 6 / textScale(scale)
      ctx.fillStyle = withAlpha(p.page, 0.85)
      ctx.fillRect(mx - w / 2, my - fs * 0.7, w, fs * 1.4)
      ctx.fillStyle = lit ? p.hold : p.ink2
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.fillText(label, mx, my)
    }
  }

  return (
    <div ref={wrapRef} className="absolute inset-0">
      {size.w > 0 && (
        <ForceGraph2D<NodeData, LinkData>
          ref={fgRef}
          width={size.w}
          height={size.h}
          graphData={data}
          backgroundColor={p.page}
          nodeId="id"
          // No hover tooltips: force-graph writes them as HTML, and engine strings render as text only.
          nodeLabel={() => ''}
          linkLabel={() => ''}
          nodeCanvasObject={drawNode}
          nodePointerAreaPaint={paintNodeArea}
          linkCanvasObject={drawLink}
          linkCanvasObjectMode={() => 'replace'}
          linkHoverPrecision={6}
          autoPauseRedraw={false}
          cooldownTicks={120}
          onEngineStop={() => {
            if (needsFit.current && fgRef.current) {
              needsFit.current = false
              fit(fgRef.current)
            }
          }}
          onNodeClick={(n) => onSelect({ kind: 'node', id: String(n.id) })}
          onLinkClick={(l) => onSelect({ kind: 'edge', edge: l.edge })}
          onBackgroundClick={() => onSelect(null)}
        />
      )}
    </div>
  )
}
