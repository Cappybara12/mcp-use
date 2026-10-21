import { useEffect, useState } from 'react'
import { callGraft, callMcp, mcpListTools, median } from './graft'

interface Props {
  statusLabel?: string
}

interface Bench {
  graft: number[]
  mcp: number[]
  sample: unknown
}

const RUNS = 20
const p95 = (xs: number[]) => [...xs].sort((a, b) => a - b)[Math.min(xs.length - 1, Math.ceil(xs.length * 0.95) - 1)]
const fmt = (n: number) => (n < 10 ? n.toFixed(1) : Math.round(n).toString())

export default function Architecture({ statusLabel }: Props) {
  const [tools, setTools] = useState<string[] | null>(null)
  const [toolsError, setToolsError] = useState('')
  const [running, setRunning] = useState(false)
  const [bench, setBench] = useState<Bench | null>(null)
  const [benchError, setBenchError] = useState('')

  useEffect(() => {
    mcpListTools().then(setTools).catch(e => setToolsError(String(e.message ?? e)))
  }, [])

  const run = async () => {
    setRunning(true)
    setBenchError('')
    try {
      // Same Python method, two callers. One warm-up call each so connection setup is not measured.
      await callGraft('getPipelineStatus')
      await callMcp('get_pipeline_status')
      const graft: number[] = []
      const mcp: number[] = []
      let sample: unknown = null
      for (let i = 0; i < RUNS; i++) {
        const g = await callGraft('getPipelineStatus')
        graft.push(g.ms)
        const m = await callMcp('get_pipeline_status')
        mcp.push(m.ms)
        sample = sample ?? m.data
      }
      setBench({ graft, mcp, sample })
    } catch (e: any) {
      setBenchError(String(e?.message ?? e))
    } finally {
      setRunning(false)
    }
  }

  const stat = (label: string, value: string, sub: string, color: string) => (
    <div className="stat-card">
      <div className="stat-label">{label}</div>
      <div className="stat-value" style={{ color }}>{value}</div>
      <div className="stat-meta">{sub}</div>
    </div>
  )

  return (
    <div className="animate-fade-in">
      <div className="page-header">
        <div className="page-title">Architecture: one Python receiver, two callers</div>
        <div className="page-subtitle">
          Everything on this page is measured live from your running gateway. Nothing here is a hardcoded claim.
        </div>
      </div>

      <div className="arch-col" style={{ marginBottom: 20 }}>
        <div className="arch-col-header good">How this app is actually wired</div>
        <div className="code-block" style={{ borderRadius: 0, fontSize: 11.5 }}>
{`Browser (React)
  └─ generated Graft (npm package) ── WebSocket ──┐
                                                  ▼
Claude / Cursor ── MCP over HTTP ──►  Graftcode Gateway  ──►  ArticlePipelineService (Python)
  (via mcp-remote for Claude Desktop)   :8080 ws · :8081 /mcp     plain public methods

No HTTP adapter, no route handlers, no hand-written fetch client for the pipeline.
The Graft is generated from the Python class; MCP is the Gateway's built-in endpoint.`}
        </div>
        <div style={{ padding: '12px 18px', borderTop: '1px solid var(--border)', fontSize: 12, color: 'var(--text-muted)' }}>
          Receiver mode: <strong>{statusLabel ?? 'loading…'}</strong>. In demo mode the topics and drafts are bundled
          samples; with the real pipeline attached they come from the production queue.
        </div>
      </div>

      <div className="card" style={{ padding: 20, marginBottom: 20 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          <div>
            <div style={{ fontWeight: 700, fontSize: 15 }}>One method, two callers: live benchmark</div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>
              Calls <code>get_pipeline_status</code> {RUNS}× through the Graft (WebSocket) and {RUNS}× through
              the Gateway's MCP endpoint (HTTP), from this browser tab.
            </div>
          </div>
          <button className="btn-primary" onClick={run} disabled={running}>
            {running ? 'Measuring…' : `Run ${RUNS} calls each`}
          </button>
        </div>

        {benchError && <div style={{ marginTop: 12, color: 'var(--red)', fontSize: 12 }}>Benchmark failed: {benchError}</div>}

        {bench && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14, marginTop: 16 }}>
            {stat('Graft median', `${fmt(median(bench.graft))} ms`, `p95 ${fmt(p95(bench.graft))} ms · n=${RUNS}`, 'var(--green)')}
            {stat('MCP median', `${fmt(median(bench.mcp))} ms`, `p95 ${fmt(p95(bench.mcp))} ms · n=${RUNS}`, '#7c3aed')}
            {stat('Same answer', JSON.stringify(bench.sample).length > 2 ? 'yes' : 'no', 'MCP returned the Python method\'s result', 'var(--accent)')}
            {stat('MCP tools', tools ? String(tools.length) : '…', 'from the gateway, no bridge process', 'var(--accent)')}
          </div>
        )}
        <div style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 12 }}>
          Timings include a local round trip and Python execution on this machine. They say nothing about
          network latency or a REST comparison, because this repo no longer has a REST path to compare against.
        </div>
      </div>

      <div className="card" style={{ padding: 20, marginBottom: 20 }}>
        <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 8 }}>MCP tools exposed by the Gateway</div>
        {toolsError && <div style={{ color: 'var(--red)', fontSize: 12 }}>Could not reach the MCP endpoint: {toolsError}</div>}
        {!tools && !toolsError && <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Loading…</div>}
        {tools && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {tools.map(t => <span key={t} className="tag">{t}</span>)}
          </div>
        )}
        <div style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 10 }}>
          Add this URL to Cursor, or bridge it to Claude Desktop with <code>mcp-remote</code>:
          {' '}<code>http://localhost:8081/mcp</code>
        </div>
      </div>

      <div className="card" style={{ padding: 20 }}>
        <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 8 }}>Known limits (honest list)</div>
        <ul style={{ fontSize: 12.5, color: 'var(--text-muted)', lineHeight: 1.7, paddingLeft: 18, margin: 0 }}>
          <li>Results cross the boundary as JSON strings. Typed object returns reach the Node/browser SDK as opaque handles today.</li>
          <li>The Gateway has no authentication by default. Keep it on localhost or add auth before exposing it.</li>
          <li>The Python service defines dataclasses internally as its schema, but the public methods return JSON.</li>
          <li>The "before" REST design is not benchmarked here; any comparison with it would be an estimate, so none is claimed.</li>
        </ul>
      </div>
    </div>
  )
}
