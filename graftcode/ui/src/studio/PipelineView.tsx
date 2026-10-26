import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'
import { Background, BackgroundVariant, Controls, Handle, Position, ReactFlow, ReactFlowProvider, addEdge, useEdgesState, useNodesState, useReactFlow } from '@xyflow/react'
import type { Connection, Edge, Node, NodeProps } from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import {
  CheckCircle2, Gauge, Globe, GitPullRequest, Library, ListOrdered, MessageSquare, PenLine, Play, Plus, Redo2, Rss, ScrollText, Search, Target, Undo2, UserCheck, AlertTriangle, Hand, Loader2,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { studio } from './api'
import { NodeDrawer } from './NodeDrawer'
import { ReviewPanel } from './ReviewPanel'
import { useStudio } from './StudioContext'
import type { NodeState, NodeTypeInfo, PlanItem, Pipeline, Run } from './types'

type StudioNodeData = { ntype: string; config: Record<string, any> }
type SNode = Node<StudioNodeData, 'studio'>
type CanvasSnapshot = { nodes: SNode[]; edges: Edge[] }

const ICONS: Record<string, LucideIcon> = {
  topic: Target, rss: Rss, scrape: Globe, corpus: Library, rulebook: ScrollText, keywords: Search, outline: ListOrdered,
  write: PenLine, seo: Gauge, review: UserCheck, reddit: MessageSquare, publish: GitPullRequest,
}

interface RunView {
  run: Run | null
  selected: string
  infos: Record<string, NodeTypeInfo>
}
const RunCtx = createContext<RunView>({ run: null, selected: '', infos: {} })

function summary(ntype: string, c: Record<string, any>): string {
  switch (ntype) {
    case 'topic': return c.topic ? String(c.topic) : 'from the plan item'
    case 'rss': return `${String(c.urls ?? '').split('\n').filter((l: string) => l.trim()).length} feed(s)`
    case 'scrape': return `${c.provider || 'direct'} · ${c.mode === 'read_urls' ? 'read URLs' : 'search + read'}`
    case 'corpus': return c.site_url ? String(c.site_url) : 'your blog'
    case 'keywords': return String(c.provider || 'manual')
    case 'reddit': return `${String(c.post_type || 'discussion').replace('_', ' ')} · ${c.provider || 'default AI'}`
    case 'outline': case 'write': return `${c.provider || 'default AI'}${c.model ? ' · ' + c.model : ''}`
    case 'publish': return c.mode === 'github_pr' ? 'GitHub pull request' : 'dry run'
    default: return ''
  }
}

function duration(s: NodeState | undefined): string {
  if (!s?.started_at || !s.finished_at) return ''
  const ms = new Date(s.finished_at).getTime() - new Date(s.started_at).getTime()
  return ms < 1000 ? `${Math.max(ms, 1)} ms` : `${(ms / 1000).toFixed(1)} s`
}

function StudioNodeCard({ id, data }: NodeProps<SNode>) {
  const { run, selected, infos } = useContext(RunCtx)
  const info = infos[data.ntype]
  const state = run?.nodes[id]
  const status = state?.status ?? 'pending'
  const enabled = data.config.enabled !== false
  const Icon = ICONS[data.ntype] ?? Target
  return (
    <div className={`snode ${status} ${selected === id ? 'selected' : ''} ${info?.ai ? 'ai' : ''} ${enabled ? '' : 'disabled'}`}>
      <Handle type="target" position={Position.Left} />
      <div className="snode-top">
        <span className="snode-icon"><Icon size={15} /></span>
        <div className="snode-title">{info?.label ?? data.ntype}</div>
        <span className={`snode-status ${status}`}>
          {status === 'running' && <Loader2 size={13} className="spin" />}
          {status === 'done' && <CheckCircle2 size={13} />}
          {status === 'error' && <AlertTriangle size={13} />}
          {status === 'awaiting_review' && <Hand size={13} />}
        </span>
      </div>
      <div className="snode-sub">{summary(data.ntype, data.config) || info?.group}</div>
      {status !== 'pending' && (
        <div className="snode-foot">
          {status === 'running' && 'Running…'}
          {status === 'done' && `Done${duration(state) ? ` · ${duration(state)}` : ''}`}
          {status === 'error' && 'Needs attention'}
          {status === 'awaiting_review' && 'Waiting for you'}
        </div>
      )}
      <Handle type="source" position={Position.Right} />
    </div>
  )
}

const nodeTypes = { studio: StudioNodeCard }

function toRF(p: Pipeline): { nodes: SNode[]; edges: Edge[] } {
  return {
    nodes: p.nodes.map(n => ({ id: n.id, type: 'studio' as const, position: n.position, data: { ntype: n.type, config: n.config } })),
    edges: p.edges.map(e => ({ id: e.id, source: e.source, target: e.target })),
  }
}

function fromRF(base: Pipeline, nodes: SNode[], edges: Edge[]): Pipeline {
  return {
    ...base,
    nodes: nodes.map(n => ({ id: n.id, type: n.data.ntype, position: { x: Math.round(n.position.x), y: Math.round(n.position.y) }, config: n.data.config })),
    edges: edges.map(e => ({ id: e.id, source: e.source, target: e.target })),
  }
}

function wouldLoop(edges: Edge[], source: string, target: string): boolean {
  const next = new Map<string, string[]>()
  for (const e of [...edges, { source, target } as Edge]) next.set(e.source, [...(next.get(e.source) ?? []), e.target])
  const seen = new Set<string>()
  const stack = [target]
  while (stack.length) {
    const cur = stack.pop() as string
    if (cur === source) return true
    if (seen.has(cur)) continue
    seen.add(cur)
    stack.push(...(next.get(cur) ?? []))
  }
  return false
}

function Canvas({ onGoToKeys }: { onGoToKeys: () => void }) {
  const { catalog, detail, wsId, fail, notify, refreshDetail } = useStudio()
  const { screenToFlowPosition, fitView } = useReactFlow()
  const [pipelineId, setPipelineId] = useState('')
  const [base, setBase] = useState<Pipeline | null>(null)
  const [nodes, setNodes, onNodesChange] = useNodesState<SNode>([])
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([])
  const [selected, setSelected] = useState('')
  const [run, setRun] = useState<Run | null>(null)
  const [running, setRunning] = useState(false)
  const [title, setTitle] = useState('')
  const [keyword, setKeyword] = useState('')
  const [planId, setPlanId] = useState('')
  const [plan, setPlan] = useState<PlanItem[]>([])
  const [reviewOpen, setReviewOpen] = useState(false)
  const [hintOpen, setHintOpen] = useState(true)
  const savedJson = useRef('')
  const loadedFor = useRef('')
  const historyCurrent = useRef<CanvasSnapshot | null>(null)
  const historyPast = useRef<CanvasSnapshot[]>([])
  const historyFuture = useRef<CanvasSnapshot[]>([])
  const [, setHistoryVersion] = useState(0)

  const infos = useMemo(() => Object.fromEntries((catalog?.nodes ?? []).map(n => [n.type, n])), [catalog])
  const groups = useMemo(() => {
    const out: Record<string, NodeTypeInfo[]> = {}
    for (const n of catalog?.nodes ?? []) (out[n.group] ??= []).push(n)
    return out
  }, [catalog])

  // choose a pipeline once the workspace is known
  useEffect(() => {
    if (!detail) return
    if (!detail.pipelines.some(p => p.id === pipelineId)) setPipelineId(detail.pipelines[0]?.id ?? '')
  }, [detail, pipelineId])

  // load the pipeline, the plan, and the latest run of this pipeline
  useEffect(() => {
    if (!wsId || !pipelineId || loadedFor.current === `${wsId}/${pipelineId}`) return
    loadedFor.current = `${wsId}/${pipelineId}`
    let cancelled = false
    ;(async () => {
      try {
        const [p, items, runs] = await Promise.all([studio.pipeline(wsId, pipelineId), studio.plan(wsId), studio.runs(wsId)])
        if (cancelled) return
        const rf = toRF(p)
        setBase(p); setNodes(rf.nodes); setEdges(rf.edges); setPlan(items)
        savedJson.current = JSON.stringify(fromRF(p, rf.nodes, rf.edges))
        historyCurrent.current = { nodes: rf.nodes, edges: rf.edges }
        historyPast.current = []
        historyFuture.current = []
        setHistoryVersion(v => v + 1)
        setSelected('')
        const last = runs.find(r => r.pipeline_id === pipelineId)
        setRun(last ? await studio.run(wsId, last.id) : null)
        window.setTimeout(() => fitView({ padding: 0.15 }), 60)
      } catch (e) { fail(e) }
    })()
    return () => { cancelled = true }
  }, [wsId, pipelineId, setNodes, setEdges, fail, fitView])

  // autosave whenever the pipeline's structure or settings change (selection and measurement changes are ignored)
  useEffect(() => {
    if (!base || !wsId) return
    const current = fromRF(base, nodes, edges)
    const json = JSON.stringify(current)
    if (json === savedJson.current) return
    const handle = window.setTimeout(async () => {
      try {
        await studio.savePipeline(wsId, current)
        savedJson.current = json
      } catch (e) {
        fail(e)
        const fresh = await studio.pipeline(wsId, base.id)   // put the canvas back to what the server accepted
        const rf = toRF(fresh)
        setNodes(rf.nodes); setEdges(rf.edges)
        savedJson.current = JSON.stringify(fromRF(fresh, rf.nodes, rf.edges))
      }
    }, 700)
    return () => window.clearTimeout(handle)
  }, [nodes, edges, base, wsId, fail, setNodes, setEdges])

  // Keep a small local undo history for canvas edits. The timeout coalesces
  // React Flow's separate node/edge updates into one undoable action.
  useEffect(() => {
    if (!base || !historyCurrent.current) return
    const handle = window.setTimeout(() => {
      const current: CanvasSnapshot = { nodes, edges }
      const previous = historyCurrent.current
      if (!previous) { historyCurrent.current = current; return }
      if (JSON.stringify(current) === JSON.stringify(previous)) return
      historyPast.current = [...historyPast.current.slice(-49), previous]
      historyCurrent.current = current
      historyFuture.current = []
      setHistoryVersion(v => v + 1)
    }, 0)
    return () => window.clearTimeout(handle)
  }, [nodes, edges, base])

  const restoreSnapshot = useCallback((snapshot: CanvasSnapshot) => {
    setNodes(snapshot.nodes)
    setEdges(snapshot.edges)
    setSelected('')
  }, [setNodes, setEdges])

  const undo = useCallback(() => {
    const previous = historyPast.current.pop()
    const current = historyCurrent.current
    if (!previous || !current) return
    historyFuture.current = [...historyFuture.current, current]
    historyCurrent.current = previous
    restoreSnapshot(previous)
    setHistoryVersion(v => v + 1)
  }, [restoreSnapshot])

  const redo = useCallback(() => {
    const next = historyFuture.current.pop()
    const current = historyCurrent.current
    if (!next || !current) return
    historyPast.current = [...historyPast.current, current]
    historyCurrent.current = next
    restoreSnapshot(next)
    setHistoryVersion(v => v + 1)
  }, [restoreSnapshot])

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null
      const editingText = target?.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(target?.tagName ?? '')
      if (editingText) return
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'z') {
        event.preventDefault()
        if (event.shiftKey) redo()
        else undo()
      } else if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'y') {
        event.preventDefault()
        redo()
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [undo, redo])

  const onConnect = useCallback((c: Connection) => {
    if (!c.source || !c.target) return
    if (c.source === c.target || wouldLoop(edges, c.source, c.target)) { notify('That connection would make a loop. Connect steps in one direction.', 'error'); return }
    setEdges(es => addEdge({ ...c, id: `${c.source}->${c.target}` }, es))
  }, [edges, notify, setEdges])

  const addNode = useCallback((type: string, at?: { x: number; y: number }) => {
    const info = infos[type]
    if (!info) return
    let id = type
    for (let n = 2; nodes.some(x => x.id === id); n++) id = `${type}-${n}`
    const position = at ?? { x: 80 + nodes.length * 24, y: 80 + nodes.length * 24 }
    setNodes(ns => [...ns, { id, type: 'studio', position, data: { ntype: type, config: { ...info.defaults } } }])
    setSelected(id)
  }, [infos, nodes, setNodes])

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    const type = e.dataTransfer.getData('application/graft-node')
    if (type) addNode(type, screenToFlowPosition({ x: e.clientX, y: e.clientY }))
  }, [addNode, screenToFlowPosition])

  const selectedNode = nodes.find(n => n.id === selected)

  const setConfig = (id: string, config: Record<string, any>) =>
    setNodes(ns => ns.map(n => (n.id === id ? { ...n, data: { ...n.data, config } } : n)))

  const deleteSelected = () => {
    setNodes(ns => ns.filter(n => n.id !== selected))
    setEdges(es => es.filter(e => e.source !== selected && e.target !== selected))
    setSelected('')
  }

  // ── running ────────────────────────────────────────────────────────────────

  const withRunning = (r: Run, nid: string): Run => ({ ...r, nodes: { ...r.nodes, [nid]: { ...r.nodes[nid], status: 'running' } } })

  const drive = async (start: Run) => {
    let r = start
    setRunning(true)
    try {
      for (const nid of r.order) {
        if (r.nodes[nid]?.status !== 'pending') continue
        setRun(withRunning(r, nid))
        r = await studio.runNode(wsId, r.id, nid)
        setRun(r)
        const st = r.nodes[nid].status
        if (st === 'error') break
        if (st === 'awaiting_review') { setReviewOpen(true); break }
      }
    } catch (e) { fail(e) } finally { setRunning(false) }
  }

  const beginRun = async (): Promise<Run | null> => {
    const planItem = plan.find(p => p.id === planId)
    const item: Record<string, string> = planItem ? { id: planItem.id, title: planItem.title, keyword: planItem.keyword, category: planItem.category, notes: planItem.notes }
      : { title: title.trim(), keyword: keyword.trim() }
    try {
      const r = await studio.startRun(wsId, pipelineId, item)
      setRun(r)
      return r
    } catch (e) { fail(e); return null }
  }

  // The engine reads each step's settings from the saved pipeline, so save pending edits before any run.
  const ensureSaved = async (): Promise<boolean> => {
    if (!base) return true
    const current = fromRF(base, nodes, edges)
    const json = JSON.stringify(current)
    if (json === savedJson.current) return true
    try {
      await studio.savePipeline(wsId, current)
      savedJson.current = json
      return true
    } catch (e) { fail(e); return false }
  }

  const runAll = async () => {
    if (!(await ensureSaved())) return
    const r = await beginRun()
    if (r) await drive(r)
  }

  const runStep = async (fromHere: boolean) => {
    if (!selected) return
    if (!(await ensureSaved())) return
    let r = run
    if (!r) r = await beginRun()
    if (!r) return
    if (fromHere) r = await studio.resetFrom(wsId, r.id, selected)
    else if (r.nodes[selected]?.status !== 'pending') r = await studio.resetFrom(wsId, r.id, selected)
    setRunning(true)
    try {
      setRun(withRunning(r, selected))
      r = await studio.runNode(wsId, r.id, selected)
      setRun(r)
      if (r.nodes[selected].status === 'awaiting_review') setReviewOpen(true)
      else if (fromHere && r.nodes[selected].status === 'done') await drive(r)
    } catch (e) { fail(e) } finally { setRunning(false) }
  }

  const afterReview = async (r: Run, approved: boolean) => {
    setRun(r); setReviewOpen(false)
    if (approved) { notify('Approved. Running the remaining steps…'); await drive(r) } else notify('Rejected. Nothing was published.')
    void refreshDetail()
  }

  const reviewNodeId = run ? Object.entries(run.nodes).find(([id, s]) => s.status === 'awaiting_review' && nodes.find(n => n.id === id)?.data.ntype === 'review')?.[0] : undefined

  const newPipeline = async () => {
    const name = window.prompt('Name for the new pipeline?', 'My pipeline')
    if (!name) return
    try {
      const live = window.confirm('Start from the live-blog template?\n\nOK = live (your own blog, no demo samples)\nCancel = demo (works offline with sample data)')
      const p = await studio.newPipeline(wsId, name, live)
      await refreshDetail()
      loadedFor.current = ''
      setPipelineId(p.id)
    } catch (e) { fail(e) }
  }

  const effectiveRunning = running || run?.status === 'running'
  const itemChosen = !!planId || title.trim() !== ''
  const infoFor = selectedNode ? infos[selectedNode.data.ntype] : undefined

  const styledEdges = useMemo(() => edges.map(e => {
    const st = run?.nodes[e.source]?.status
    return { ...e, animated: st === 'running', className: st === 'done' ? 'edge-done' : st === 'running' ? 'edge-running' : '' }
  }), [edges, run])

  return (
    <RunCtx.Provider value={{ run, selected, infos }}>
      <div className="studio-grid">
        <aside className="palette">
          <div className="palette-title">Steps</div>
          <div className="palette-hint">Drag a step onto the canvas, then connect it to others.</div>
          {Object.entries(groups).map(([group, list]) => (
            <div key={group} className="palette-group">
              <div className="label">{group}</div>
              {list.map(n => {
                const Icon = ICONS[n.type] ?? Target
                return (
                  <div key={n.type} className="palette-item" draggable title={n.description}
                    onDragStart={e => { e.dataTransfer.setData('application/graft-node', n.type); e.dataTransfer.effectAllowed = 'move' }}
                    onDoubleClick={() => addNode(n.type)}>
                    <Icon size={14} /><span>{n.label}</span><button className="icon-btn tiny" onClick={() => addNode(n.type)} aria-label={`Add ${n.label}`}><Plus size={12} /></button>
                  </div>
                )
              })}
            </div>
          ))}
        </aside>

        <section className="canvas-col">
          <div className="toolbar">
            <select value={pipelineId} onChange={e => { loadedFor.current = ''; setPipelineId(e.target.value) }} aria-label="Pipeline">
              {(detail?.pipelines ?? []).map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
            <button className="btn-ghost small" onClick={newPipeline}><Plus size={13} /> New</button>
            <button className="icon-btn tiny" onClick={undo} disabled={!historyPast.current.length} title="Undo (Ctrl/Cmd+Z)" aria-label="Undo"><Undo2 size={14} /></button>
            <button className="icon-btn tiny" onClick={redo} disabled={!historyFuture.current.length} title="Redo (Ctrl/Cmd+Shift+Z)" aria-label="Redo"><Redo2 size={14} /></button>
            <span className="toolbar-sep" />
            <select value={planId} onChange={e => setPlanId(e.target.value)} aria-label="Run for">
              <option value="">Run for a topic I type…</option>
              {plan.filter(p => p.status !== 'published').map(p => <option key={p.id} value={p.id}>{p.title}</option>)}
            </select>
            {!planId && (
              <>
                <input className="tb-input" placeholder="Topic, e.g. How to read a retention table" value={title} onChange={e => setTitle(e.target.value)} />
                <input className="tb-input short" placeholder="Keyword (optional)" value={keyword} onChange={e => setKeyword(e.target.value)} />
              </>
            )}
            <button className="btn-primary" onClick={runAll} disabled={effectiveRunning || !itemChosen} title={!itemChosen ? 'Type a topic or pick a plan item first' : ''}>
              <Play size={14} /> {effectiveRunning ? 'Running…' : 'Run pipeline'}
            </button>
            {run && !effectiveRunning && <button className="btn-ghost small" onClick={() => { setRun(null); setReviewOpen(false) }}>Clear run</button>}
            {reviewNodeId && !reviewOpen && <button className="btn-secondary small attention" onClick={() => setReviewOpen(true)}><Hand size={13} /> Review draft</button>}
          </div>
          {hintOpen && !run && (
            <div className="hint-bar">
              <span><strong>1</strong> Click a step to edit it or add your instructions</span>
              <span><strong>2</strong> Type a topic above and press Run pipeline</span>
              <span><strong>3</strong> Approve at Human review before anything is published</span>
              <button className="icon-btn tiny" onClick={() => setHintOpen(false)} aria-label="Hide tips">×</button>
            </div>
          )}
          <div className="canvas" onDrop={onDrop} onDragOver={e => { e.preventDefault(); e.dataTransfer.dropEffect = 'move' }}>
            <ReactFlow nodes={nodes} edges={styledEdges} nodeTypes={nodeTypes} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange}
              onConnect={onConnect} onNodeClick={(_, n) => setSelected(n.id)} onPaneClick={() => setSelected('')}
              deleteKeyCode={['Backspace', 'Delete']} minZoom={0.25} maxZoom={1.6} fitView fitViewOptions={{ padding: 0.1 }} onInit={() => fitView({ padding: 0.1 })} proOptions={{ hideAttribution: true }}>
              <Background variant={BackgroundVariant.Dots} gap={22} size={1.2} color="#d4d4d8" />
              <Controls showInteractive={false} />
            </ReactFlow>
          </div>
          <div className="legend">
            <span><i className="lg idle" /> not run</span><span><i className="lg running" /> running</span><span><i className="lg done" /> done</span>
            <span><i className="lg wait" /> needs you</span><span><i className="lg err" /> error</span><span className="grow" />
            <span className="muted">Changes save automatically</span>
          </div>
        </section>

        {reviewOpen && run && reviewNodeId ? (
          <ReviewPanel ws={wsId} run={run} reviewNodeId={reviewNodeId} onDecided={afterReview} onClose={() => setReviewOpen(false)} />
        ) : selectedNode && infoFor && catalog && detail ? (
          <NodeDrawer key={selectedNode.id} info={infoFor} nodeId={selectedNode.id} config={selectedNode.data.config}
            state={run?.nodes[selectedNode.id]} catalog={catalog} secrets={detail.secrets} templates={detail.templates ?? []} wsConfig={detail.config}
            // A Topic node can provide its own fallback topic. Let its drawer run
            // when that field is filled, even if the top-toolbar run target is empty.
            canRun={itemChosen || !!run || (selectedNode?.data.ntype === 'topic' && !!String(selectedNode.data.config.topic ?? '').trim())} busy={effectiveRunning}
            onChange={cfg => setConfig(selectedNode.id, cfg)} onClose={() => setSelected('')} onDelete={deleteSelected}
            onRunStep={() => runStep(false)} onRunFrom={() => runStep(true)} onGoToKeys={onGoToKeys}
            onSaveTemplate={async template => { await studio.saveTemplate(wsId, template); await refreshDetail(); notify('Template saved to this workspace.') }}
            onPreview={async () => {
              try { return await studio.previewPrompt(wsId, pipelineId, selectedNode.id, run?.id ?? '') } catch (e) { fail(e); return null }
            }} />
        ) : null}
      </div>
    </RunCtx.Provider>
  )
}

export function PipelineView({ onGoToKeys }: { onGoToKeys: () => void }) {
  return (
    <ReactFlowProvider>
      <Canvas onGoToKeys={onGoToKeys} />
    </ReactFlowProvider>
  )
}
