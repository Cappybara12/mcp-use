import { useState, useEffect } from 'react'
import {
  Zap,
  LayoutDashboard,
  Flame,
  BookOpen,
  ShieldCheck,
  GitPullRequest,
  Code2,
  Activity,
  RefreshCw,
  Sparkles,
  ExternalLink,
  Terminal,
  Cpu,
  Layers,
  ChevronRight,
  Scan,
  LightbulbIcon,
  Network,
  CalendarDays,
  ScrollText,
  Settings as SettingsIcon,
  X,
} from 'lucide-react'
import confetti from 'canvas-confetti'
import './studio/studio.css'
import { StudioProvider, useStudio } from './studio/StudioContext'
import { PipelineView } from './studio/PipelineView'
import { Planner } from './studio/Planner'
import { RulebookView } from './studio/Rulebook'
import { SettingsView } from './studio/Settings'
import { WorkspaceBar } from './studio/WorkspaceBar'
import { GraftStrip } from './studio/GraftStrip'
import { callGraft, mcpListTools } from './graft'
import Architecture from './Architecture'

interface Topic {
  id: string
  title: string
  filename: string
  category: string
  sources_count: number
  snippet: string
}

interface Draft {
  filename: string
  title: string
  word_count: number
  size_bytes: number
  updated_at: string
}

interface PipelineStatus {
  status: string
  runtime: string
  transport: string
  active_brand: string
  queue_stats: { pending_topics_count: number; completed_drafts_count: number }
  providers: { primary_llm: string; research_engine: string; media_engine: string }
  timestamp: string
}

interface RpcLog {
  id: string
  method: string
  time: string
  durationMs: number
  status: 'ok' | 'err'
}

type Tab = 'studio' | 'planner' | 'rulebook' | 'settings' | 'overview' | 'queue' | 'writer' | 'auditor' | 'publisher' | 'architecture'

const STUDIO_NAV = [
  { id: 'studio',   label: 'Pipeline',        icon: Network },
  { id: 'planner',  label: 'Content planner', icon: CalendarDays },
  { id: 'rulebook', label: 'Rulebook',        icon: ScrollText },
  { id: 'settings', label: 'Settings & keys', icon: SettingsIcon },
]

const SIDEBAR_NAV = [
  { id: 'overview',      label: 'Dashboard',       icon: LayoutDashboard },
  { id: 'queue',         label: 'Topic Queue',      icon: Flame },
  { id: 'writer',        label: 'Draft Studio',     icon: BookOpen },
  { id: 'auditor',       label: 'Style Auditor',    icon: ShieldCheck },
  { id: 'publisher',     label: 'GitHub Staging',   icon: GitPullRequest },
  { id: 'architecture',  label: 'Architecture',     icon: Code2 },
]

export default function App() {
  return (
    <StudioProvider>
      <Shell />
    </StudioProvider>
  )
}

function Shell() {
  const { detail, toasts, dismiss, connected } = useStudio()
  const [tab, setTab] = useState<Tab>('studio')
  const [status, setStatus] = useState<PipelineStatus | null>(null)
  const [topics, setTopics] = useState<Topic[]>([])
  const [drafts, setDrafts] = useState<Draft[]>([])
  const [selectedDraft, setSelectedDraft] = useState('')
  const [draftContent, setDraftContent] = useState('')
  const [auditResult, setAuditResult] = useState<any>(null)
  const [sourcesList, setSourcesList] = useState<any[]>([])
  const [sourcesModal, setSourcesModal] = useState(false)
  const [sourcesLoading, setSourcesLoading] = useState(false)
  const [savedContent, setSavedContent] = useState('')
  const [activeSourcesTopic, setActiveSourcesTopic] = useState('')
  const [isGenerating, setIsGenerating] = useState(false)
  const [genStep, setGenStep] = useState(0)
  const [genTopic, setGenTopic] = useState('')
  const [loading, setLoading] = useState(false)
  const [rpcLogs, setRpcLogs] = useState<RpcLog[]>([])
  const [mcpTools, setMcpTools] = useState<string[] | null>(null)
  const [catFilter, setCatFilter] = useState('All')
  const [prResult, setPrResult] = useState<any>(null)
  const [scanResult, setScanResult] = useState<any>(null)
  const [suggestion, setSuggestion] = useState<any>(null)
  const [scanLoading, setScanLoading] = useState(false)
  const [suggestLoading, setSuggestLoading] = useState(false)

  const callGraftRpc = async (method: string, body: any = {}) => {
    const t0 = Date.now()
    // Argument order of the generated Graft methods (the Python signatures).
    const args: Record<string, unknown[]> = {
      getTopicSources: [body.topic ?? ''],
      writeArticle: [body.topic ?? '', body.skipResearch ?? false, body.extraResearch ?? ''],
      getDraft: [body.filename ?? ''],
      saveDraft: [body.filename ?? '', body.content ?? ''],
      runStyleCheck: [body.filename ?? ''],
      pushToGithub: [body.filename ?? ''],
    }
    try {
      const { data } = await callGraft(method, ...(args[method] ?? []))
      setRpcLogs(prev => [
        { id: Math.random().toString(36).slice(2), method: `pipeline.${method}()`, time: new Date().toLocaleTimeString(), durationMs: Date.now() - t0, status: 'ok' },
        ...prev.slice(0, 19),
      ])
      return data
    } catch (err: any) {
      setRpcLogs(prev => [
        { id: Math.random().toString(36).slice(2), method: `pipeline.${method}()`, time: new Date().toLocaleTimeString(), durationMs: Date.now() - t0, status: 'err' },
        ...prev.slice(0, 19),
      ])
      return { error: err?.message || String(err) }
    }
  }

  const refreshAll = async () => {
    setLoading(true)
    const [s, t, d] = await Promise.all([
      callGraftRpc('getPipelineStatus'),
      callGraftRpc('listPendingTopics'),
      callGraftRpc('listDrafts'),
    ])
    if (s) setStatus(s)
    if (t && Array.isArray(t)) setTopics(t)
    if (d && Array.isArray(d)) {
      setDrafts(d)
      if (d.length > 0 && !selectedDraft) {
        setSelectedDraft(d[0].filename)
        loadDraft(d[0].filename)
      }
    }
    setLoading(false)
  }

  useEffect(() => { refreshAll() }, [])
  useEffect(() => { mcpListTools().then(setMcpTools).catch(() => setMcpTools(null)) }, [])

  const loadDraft = async (fn: string) => {
    const r = await callGraftRpc('getDraft', { filename: fn })
    if (r?.content) { setDraftContent(r.content); setSavedContent(r.content); setSelectedDraft(fn) }
  }

  const dirty = !!selectedDraft && draftContent !== savedContent

  const handleSave = async () => {
    setLoading(true)
    const r = await callGraftRpc('saveDraft', { filename: selectedDraft, content: draftContent })
    if (r && !r.error) {
      setSavedContent(draftContent)
      const d = await callGraftRpc('listDrafts')
      if (Array.isArray(d)) setDrafts(d)
    }
    setLoading(false)
  }

  const handleStyleCheck = async (fn: string) => {
    setLoading(true)
    // The audit reads the saved file, so save pending edits first.
    if (dirty && fn === selectedDraft) {
      const saved = await callGraftRpc('saveDraft', { filename: fn, content: draftContent })
      if (saved && !saved.error) setSavedContent(draftContent)
    }
    const r = await callGraftRpc('runStyleCheck', { filename: fn })
    setAuditResult(r)
    setLoading(false)
    setTab('auditor')
  }

  const handleGenerate = async (topicTitle: string) => {
    setIsGenerating(true); setGenTopic(topicTitle); setTab('writer')
    for (let i = 1; i <= 4; i++) {
      setGenStep(i)
      await new Promise(r => setTimeout(r, 700 + i * 100))
    }
    const result = await callGraftRpc('writeArticle', { topic: topicTitle })
    setIsGenerating(false); setGenStep(0)
    if (result?.filename) {
      confetti({ particleCount: 70, spread: 55, origin: { y: 0.7 } })
      await refreshAll()
      await loadDraft(result.filename)
    }
  }

  const handlePush = async (fn: string) => {
    setLoading(true)
    const r = await callGraftRpc('pushToGithub', { filename: fn })
    setPrResult(r); setLoading(false); setTab('publisher')
    if (r?.status === 'pr_created') {
      confetti({ particleCount: 80, spread: 65, origin: { y: 0.6 } })
    }
  }

  const handleScan = async () => {
    setScanLoading(true)
    const r = await callGraftRpc('runScanner')
    setScanResult(r); setScanLoading(false)
    await refreshAll()
  }

  const handleSuggest = async () => {
    setSuggestLoading(true)
    const r = await callGraftRpc('suggestNextArticle')
    setSuggestion(r); setSuggestLoading(false)
  }

  const openSources = async (title: string) => {
    setActiveSourcesTopic(title); setSourcesModal(true)
    setSourcesList([]); setSourcesLoading(true)
    const r = await callGraftRpc('getTopicSources', { topic: title })
    if (Array.isArray(r)) setSourcesList(r)
    setSourcesLoading(false)
  }

  const brandName = status?.active_brand?.split(' (')[0] ?? 'Content Engine'
  const isStudioTab = tab === 'studio' || tab === 'planner' || tab === 'rulebook' || tab === 'settings'

  const filtered = catFilter === 'All' ? topics : topics.filter(t => t.category === catFilter)

  return (
    <div className="shell">
      {/* ── Sidebar ── */}
      <nav className="sidebar">
        {/* Logo */}
        <div className="sidebar-logo" style={{ marginBottom: 8 }}>
          <div className="sidebar-logo-icon">
            <Zap size={16} color="#fff" />
          </div>
          <span className="sidebar-logo-text">Graft Studio</span>
          <span className="sidebar-badge">GRAFT</span>
        </div>

        <WorkspaceBar />

        <div className="sidebar-section">
          <div className="sidebar-section-label">Studio</div>
          {STUDIO_NAV.map(({ id, label, icon: Icon }) => (
            <button key={id} className={`sidebar-item ${tab === id ? 'active' : ''}`} onClick={() => setTab(id as Tab)}>
              <Icon size={15} />
              {label}
            </button>
          ))}
        </div>

        <div className="sidebar-divider" />

        <div className="sidebar-section">
          <div className="sidebar-section-label">Original pipeline</div>
          {SIDEBAR_NAV.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              className={`sidebar-item ${tab === id ? 'active' : ''}`}
              onClick={() => setTab(id as Tab)}
            >
              <Icon size={15} />
              {label}
            </button>
          ))}
        </div>

        <div className="sidebar-divider" />

        <div className="sidebar-section">
          <div className="sidebar-section-label">System</div>
          <div className="sidebar-item">
            <Activity size={15} />
            Gateway: 8080
            <span className="dot dot-green" style={{ marginLeft: 'auto' }} />
          </div>
          <div className="sidebar-item">
            <Cpu size={15} />
            {mcpTools ? `MCP: ${mcpTools.length} tools` : 'MCP: offline'}
            <span className={mcpTools ? 'dot dot-green' : 'dot'} style={{ marginLeft: 'auto' }} />
          </div>
        </div>

        <div style={{ marginTop: 'auto', padding: '16px 12px' }}>
          <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.25)', lineHeight: 1.5 }}>
            Graftcode Gateway v1.4.10<br />
            Python Receiver ↔ TypeScript
          </div>
        </div>
      </nav>

      {/* ── Main ── */}
      <div className="main">
        {/* Topbar */}
        <div className="topbar">
          <div className="topbar-left">
            <span style={{ color: '#9ca3af' }}>{isStudioTab ? (detail?.config.name || 'Workspace') : brandName}</span>
            <ChevronRight size={14} color="#d1d5db" />
            <span className="topbar-breadcrumb">
              {[...STUDIO_NAV, ...SIDEBAR_NAV].find(n => n.id === tab)?.label || 'Dashboard'}
            </span>
          </div>
          <div className="topbar-right">
            {!isStudioTab && <>
            <button className="btn-ghost" onClick={refreshAll} disabled={loading}>
              <RefreshCw size={14} className={loading ? 'spin' : ''} />
              Sync
            </button>
            <button className="btn-primary" onClick={() => handleGenerate('The Remote Worker\'s Guide to South Goa Beach Villages')} disabled={isGenerating}>
              <Sparkles size={14} />
              Auto-Pilot Draft
            </button>
            </>}
          </div>
        </div>

        {!connected && <div className="note" style={{ margin: 12 }}>Cannot reach the Graftcode gateway. Start it with <code>bash scripts/start.sh</code>, then reload.</div>}

        {/* Page */}
        <div className={isStudioTab ? 'page full' : 'page'}>
          {tab === 'studio' && <PipelineView onGoToKeys={() => setTab('settings')} />}
          {tab === 'planner' && <Planner onOpenPipeline={() => setTab('studio')} />}
          {tab === 'rulebook' && <RulebookView />}
          {tab === 'settings' && <SettingsView />}

          {/* ══════════ OVERVIEW ══════════ */}
          {tab === 'overview' && (
            <div className="animate-fade-in">
              <div className="page-header">
                <div className="page-title">Dashboard</div>
                <div className="page-subtitle">{brandName} content engine — a Python pipeline called through Graftcode</div>
              </div>

              {/* Stat cards */}
              <div className="stat-grid">
                <div className="stat-card">
                  <div className="stat-label">
                    Graftcode Package
                    <Layers size={14} color="var(--graft)" />
                  </div>
                  <div className="stat-value accent" style={{ fontSize: 16, fontFamily: 'var(--font-mono)', letterSpacing: 0 }}>
                    @graft/pypi-wayzyy
                  </div>
                  <div className="stat-meta">Hypertube binary RPC over WebSocket</div>
                </div>

                <div className="stat-card">
                  <div className="stat-label">
                    Pending Topics
                    <Flame size={14} color="var(--accent)" />
                  </div>
                  <div className="stat-value">{status?.queue_stats.pending_topics_count ?? '—'}</div>
                  <div className="stat-meta">From social feeds & news</div>
                </div>

                <div className="stat-card">
                  <div className="stat-label">
                    Drafts Generated
                    <BookOpen size={14} color="#111" />
                  </div>
                  <div className="stat-value green">{drafts.length || '0'}</div>
                  <div className="stat-meta">Drafts in the current pipeline</div>
                </div>

                <div className="stat-card">
                  <div className="stat-label">
                    Claude MCP
                    <Cpu size={14} color="var(--graft)" />
                  </div>
                  <div className="stat-value" style={{ fontSize: 16, color: 'var(--graft)' }}>{mcpTools ? `${mcpTools.length} tools` : 'Offline'}</div>
                  <div className="stat-meta">{mcpTools ? 'served by the Gateway at /mcp' : 'Gateway MCP endpoint unreachable'}</div>
                </div>
              </div>

              {/* MCP Quick Actions */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 18, marginBottom: 20 }}>
                {/* Scanner */}
                <div className="card" style={{ padding: 22 }}>
                  <div className="section-header">
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <Scan size={16} color="var(--accent)" />
                      <span className="section-title">Run Topic Scanner</span>
                    </div>
                    <span className="badge badge-pink">MCP Tool</span>
                  </div>
                  <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 16, lineHeight: 1.55 }}>
                    Runs the trend scanner (social, forums and the web) and adds new topics to the review queue. Skipped in demo mode.
                  </p>
                  {scanResult && (
                    <div style={{ marginBottom: 14, padding: '10px 14px', background: 'var(--bg-surface)', borderRadius: 8, border: '1px solid var(--border)', fontSize: 12 }}>
                      <div style={{ fontWeight: 600, color: 'var(--green)', marginBottom: 4 }}>✓ Scanner completed</div>
                      <div style={{ color: 'var(--text-muted)' }}>{scanResult.message} Pending topics: <strong style={{ color: 'var(--text-primary)' }}>{scanResult.pending_topics_count}</strong></div>
                    </div>
                  )}
                  <button className="btn-primary" onClick={handleScan} disabled={scanLoading} style={{ width: '100%', justifyContent: 'center' }}>
                    <Scan size={14} className={scanLoading ? 'spin' : ''} />
                    {scanLoading ? 'Scanning…' : 'Scan for New Topics'}
                  </button>
                </div>

                {/* Suggest */}
                <div className="card" style={{ padding: 22 }}>
                  <div className="section-header">
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <LightbulbIcon size={16} color="var(--accent)" />
                      <span className="section-title">Suggest Next Article</span>
                    </div>
                    <span className="badge badge-pink">MCP Tool</span>
                  </div>
                  <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 16, lineHeight: 1.55 }}>
                    Ranks pending topics by business-keyword match and number of trend sources, skipping topics that already have a draft.
                  </p>
                  {suggestion && (
                    <div style={{ marginBottom: 14, padding: '10px 14px', background: 'var(--bg-surface)', borderRadius: 8, border: '1px solid var(--border)', fontSize: 12 }}>
                      <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: 4 }}>{suggestion.topic}</div>
                      <div style={{ color: 'var(--text-muted)', lineHeight: 1.5 }}>{suggestion.rationale}</div>
                      <div style={{ marginTop: 8, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                        {suggestion.matched_signals?.map((k: string) => <span key={k} className="tag">{k}</span>)}
                      </div>
                    </div>
                  )}
                  <button className="btn-secondary" onClick={handleSuggest} disabled={suggestLoading} style={{ width: '100%', justifyContent: 'center' }}>
                    <LightbulbIcon size={14} className={suggestLoading ? 'spin' : ''} />
                    {suggestLoading ? 'Thinking…' : 'Get Suggestion'}
                  </button>
                </div>
              </div>

              {/* Stack + RPC logs */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 18 }}>
                <div className="card" style={{ padding: 22 }}>
                  <div className="section-header">
                    <span className="section-title">Active Architecture</span>
                  </div>
                  <div className="divider" style={{ marginBottom: 14 }} />
                  {[
                    { label: 'Receiver Host', value: 'Graftcode Gateway v1.4.10', ok: true },
                    { label: 'Transport',     value: 'Hypertube Binary / WebSocket', ok: true },
                    { label: 'Primary LLM',   value: status?.providers.primary_llm ?? 'loading…', ok: !!status },
                    { label: 'Media Engine',  value: status?.providers.media_engine ?? 'loading…', ok: !!status },
                    { label: 'Brand config', value: status?.active_brand ?? 'loading…', ok: !!status },
                    { label: 'MCP Surface',   value: mcpTools ? `${mcpTools.length} tools at gateway /mcp` : 'unreachable', ok: !!mcpTools },
                  ].map(row => (
                    <div key={row.label} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '9px 0', borderBottom: '1px solid var(--border)', fontSize: 13 }}>
                      <span style={{ color: 'var(--text-muted)' }}>{row.label}</span>
                      <span style={{ fontWeight: 500, color: row.ok ? 'var(--text-primary)' : 'var(--red)', display: 'flex', alignItems: 'center', gap: 6 }}>
                        {row.ok && <span className="dot dot-green" />}
                        {row.value}
                      </span>
                    </div>
                  ))}
                </div>

                <div className="card" style={{ padding: 22, display: 'flex', flexDirection: 'column' }}>
                  <div className="section-header">
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <Terminal size={15} color="var(--graft)" />
                      <span className="section-title">Live RPC Calls</span>
                    </div>
                    <span style={{ fontSize: 11, color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>Hypertube</span>
                  </div>
                  <div className="rpc-terminal" style={{ flex: 1 }}>
                    {rpcLogs.length === 0 ? (
                      <span style={{ color: '#555', margin: 'auto', textAlign: 'center', display: 'block' }}>Listening for method invocations…</span>
                    ) : rpcLogs.map(log => (
                      <div key={log.id} style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #1a1a1a', paddingBottom: 5 }}>
                        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                          <span style={{ color: log.status === 'ok' ? '#fff' : '#ef4444' }}>➔</span>
                          <span style={{ color: '#e2e8f0', fontWeight: 600 }}>{log.method}</span>
                        </div>
                        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                          <span style={{ color: '#555', fontSize: 10 }}>{log.time}</span>
                          <span style={{ background: '#1a1a1a', color: 'var(--accent)', padding: '1px 6px', borderRadius: 4, fontSize: 10 }}>{log.durationMs}ms</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ══════════ TOPIC QUEUE ══════════ */}
          {tab === 'queue' && (
            <div className="animate-fade-in">
              <div className="page-header">
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
                  <div>
                    <div className="page-title">Topic Queue</div>
                    <div className="page-subtitle">Discovered from social feeds & news — click Generate to write any topic</div>
                  </div>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <button className="btn-secondary" onClick={handleScan} disabled={scanLoading}>
                      <Scan size={14} className={scanLoading ? 'spin' : ''} />
                      {scanLoading ? 'Scanning…' : 'Scan New Topics'}
                    </button>
                    <button className="btn-secondary" onClick={handleSuggest} disabled={suggestLoading}>
                      <LightbulbIcon size={14} />
                      Suggest Best
                    </button>
                  </div>
                </div>

                {suggestion && (
                  <div className="card" style={{ padding: 14, marginTop: 14, display: 'flex', gap: 12, alignItems: 'flex-start' }}>
                    <LightbulbIcon size={15} color="var(--accent)" style={{ marginTop: 2 }} />
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 13, fontWeight: 600 }}>AI Suggestion: {suggestion.topic}</div>
                      <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 3 }}>{suggestion.rationale}</div>
                    </div>
                    <button className="btn-primary" onClick={() => handleGenerate(suggestion.topic)}>
                      <Sparkles size={13} /> Write This
                    </button>
                  </div>
                )}
              </div>

              {/* Filters */}
              <div style={{ display: 'flex', gap: 6, marginBottom: 18 }}>
                {['All', ...Array.from(new Set(topics.map(t => t.category)))].map(c => (
                  <button
                    key={c}
                    onClick={() => setCatFilter(c)}
                    style={{
                      padding: '5px 14px',
                      borderRadius: 20,
                      fontSize: 12,
                      fontWeight: 600,
                      border: '1px solid var(--border)',
                      background: catFilter === c ? 'var(--accent)' : 'var(--bg)',
                      color: catFilter === c ? '#fff' : 'var(--text-muted)',
                      cursor: 'pointer',
                      transition: 'all 0.15s',
                    }}
                  >{c}</button>
                ))}
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: 14 }}>
                {filtered.map(topic => (
                  <div key={topic.id} className="topic-card">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span className="badge badge-gray">{topic.category}</span>
                      <button
                        className="btn-ghost"
                        style={{ fontSize: 12, padding: '4px 8px' }}
                        onClick={() => openSources(topic.title)}
                      >
                        <ExternalLink size={11} />
                        {topic.sources_count} {topic.sources_count === 1 ? 'Source' : 'Sources'}
                      </button>
                    </div>
                    <div style={{ fontSize: 14, fontWeight: 600, lineHeight: 1.4 }}>{topic.title}</div>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.5 }}>{topic.snippet}</div>
                    <div className="divider" />
                    <button
                      className="btn-primary"
                      onClick={() => handleGenerate(topic.title)}
                      disabled={isGenerating}
                      style={{ width: '100%', justifyContent: 'center' }}
                    >
                      <Sparkles size={13} />
                      Generate Draft
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ══════════ DRAFT STUDIO ══════════ */}
          {tab === 'writer' && (
            <div className="animate-fade-in">
              <div className="page-header">
                <div className="page-title">Draft Studio</div>
                <div className="page-subtitle">View, edit, and manage all generated drafts</div>
              </div>

              {isGenerating && (
                <div className="card" style={{ padding: 20, marginBottom: 18, borderColor: 'var(--accent-border)', background: 'rgba(255,106,19,0.04)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
                    <Sparkles size={17} color="var(--accent)" className="pulse-indicator" />
                    <span style={{ fontWeight: 700, fontSize: 15 }}>Generating: "{genTopic}"</span>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10 }}>
                    {[
                      { step: 1, title: 'Keyword Extraction', desc: 'Analyzing search intent' },
                      { step: 2, title: 'Source Mining',      desc: 'Verifying citations' },
                      { step: 3, title: 'Brand Tone Draft',   desc: 'Writing via Groq/Kimi' },
                      { step: 4, title: 'Pexels Images',      desc: 'Sourcing licensed photos' },
                    ].map(s => (
                      <div
                        key={s.step}
                        style={{
                          padding: 12,
                          borderRadius: 8,
                          background: genStep >= s.step ? 'rgba(255,106,19,0.08)' : 'var(--bg-surface)',
                          border: `1px solid ${genStep === s.step ? 'var(--accent)' : genStep > s.step ? 'var(--accent-border)' : 'var(--border)'}`,
                          transition: 'all 0.3s',
                        }}
                      >
                        <div style={{ fontSize: 10, fontWeight: 700, color: genStep >= s.step ? 'var(--accent)' : 'var(--text-dim)', marginBottom: 4 }}>STEP 0{s.step}</div>
                        <div style={{ fontSize: 13, fontWeight: 600 }}>{s.title}</div>
                        <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>{s.desc}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr', gap: 18 }}>
                {/* Draft list */}
                <div className="card" style={{ padding: 14, maxHeight: '72vh', overflowY: 'auto' }}>
                  <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-muted)', marginBottom: 12 }}>
                    Drafts ({drafts.length})
                  </div>
                  {drafts.length === 0 && (
                    <div style={{ fontSize: 13, color: 'var(--text-dim)', textAlign: 'center', padding: 24 }}>No drafts yet.<br />Generate one from the Topic Queue.</div>
                  )}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                    {drafts.map(d => (
                      <div
                        key={d.filename}
                        onClick={() => loadDraft(d.filename)}
                        style={{
                          padding: '10px 12px',
                          borderRadius: 8,
                          background: selectedDraft === d.filename ? 'var(--accent-light)' : 'transparent',
                          border: `1px solid ${selectedDraft === d.filename ? 'var(--accent-border)' : 'var(--border)'}`,
                          cursor: 'pointer',
                          transition: 'all 0.15s',
                        }}
                      >
                        <div style={{ fontSize: 13, fontWeight: 600, lineHeight: 1.3, marginBottom: 6 }}>{d.title}</div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--text-dim)' }}>
                          <span>{d.word_count} words</span>
                          <span>{d.updated_at}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Editor */}
                <div className="card" style={{ padding: 20, display: 'flex', flexDirection: 'column', maxHeight: '72vh' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14, paddingBottom: 14, borderBottom: '1px solid var(--border)' }}>
                    <div>
                      <div style={{ fontWeight: 700, fontSize: 15 }}>{selectedDraft || 'No draft selected'}</div>
                      <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Managed via Python ArticlePipelineService.get_draft()</div>
                    </div>
                    <div style={{ display: 'flex', gap: 8 }}>
                      <button className="btn-secondary" onClick={handleSave} disabled={!dirty || loading}>
                        {dirty ? 'Save changes •' : 'Saved'}
                      </button>
                      <button className="btn-secondary" onClick={() => handleStyleCheck(selectedDraft)} disabled={!selectedDraft || loading}>
                        <ShieldCheck size={13} />
                        Style Check
                      </button>
                      <button className="btn-primary" onClick={() => handlePush(selectedDraft)} disabled={!selectedDraft || loading}>
                        <GitPullRequest size={13} />
                        Stage PR
                      </button>
                    </div>
                  </div>
                  <textarea
                    value={draftContent}
                    onChange={e => setDraftContent(e.target.value)}
                    style={{
                      flex: 1, resize: 'none', minHeight: 360,
                      background: '#fafafa', border: '1px solid var(--border)',
                      borderRadius: 8, padding: 16, fontFamily: 'var(--font-mono)',
                      fontSize: 12.5, lineHeight: 1.7, color: '#111', outline: 'none',
                    }}
                  />
                </div>
              </div>
            </div>
          )}

          {/* ══════════ BRAND AUDITOR ══════════ */}
          {tab === 'auditor' && (
            <div className="animate-fade-in">
              <div className="page-header">
                <div className="page-title">Brand Style Auditor</div>
                <div className="page-subtitle">Heuristic AI-cliché, passive-voice and structure check — powered by Python run_style_check()</div>
              </div>

              {!auditResult ? (
                <div className="card" style={{ padding: 40, textAlign: 'center' }}>
                  <ShieldCheck size={40} color="var(--accent)" style={{ margin: '0 auto 14px' }} />
                  <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 8 }}>No audit run yet</div>
                  <div style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 20 }}>Go to Draft Studio, select a draft, and click "Style Check"</div>
                  <button className="btn-secondary" onClick={() => setTab('writer')}>Go to Draft Studio</button>
                </div>
              ) : (
                <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr', gap: 18 }}>
                  <div className="card" style={{ padding: 24, textAlign: 'center' }}>
                    <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.07em', color: 'var(--text-muted)', marginBottom: 12 }}>Brand Score</div>
                    <div style={{
                      width: 100, height: 100, borderRadius: '50%',
                      background: auditResult.brand_score >= 85 ? 'rgba(0,0,0,0.06)' : 'rgba(255,106,19,0.12)',
                      border: `4px solid ${auditResult.brand_score >= 85 ? 'var(--green)' : 'var(--accent)'}`,
                      display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
                      margin: '0 auto 14px',
                    }}>
                      <span style={{ fontSize: 28, fontWeight: 800, color: auditResult.brand_score >= 85 ? 'var(--green)' : 'var(--accent)' }}>{auditResult.brand_score}</span>
                      <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>/100</span>
                    </div>
                    <span className={`badge ${auditResult.brand_score >= 85 ? 'badge-green' : 'badge-pink'}`} style={{ margin: '0 auto' }}>
                      {auditResult.verdict}
                    </span>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                    {auditResult.ai_cliches_found?.length > 0 && (
                      <div className="card" style={{ padding: 18 }}>
                        <div style={{ fontWeight: 700, marginBottom: 10, color: 'var(--red)', fontSize: 13 }}>⚠ AI Clichés Found</div>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                          {auditResult.ai_cliches_found.map((w: string) => (
                            <span key={w} style={{ background: 'rgba(239,68,68,0.08)', color: 'var(--red)', border: '1px solid rgba(239,68,68,0.2)', borderRadius: 4, padding: '2px 8px', fontSize: 12, fontWeight: 600 }}>{w}</span>
                          ))}
                        </div>
                      </div>
                    )}

                    <div className="card" style={{ padding: 18 }}>
                      <div style={{ fontWeight: 700, marginBottom: 10, fontSize: 13, color: 'var(--green)' }}>✓ Passed Checks</div>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                        {auditResult.passed_checks?.map((c: string) => (
                          <div key={c} style={{ fontSize: 13, color: 'var(--text-muted)', display: 'flex', gap: 8 }}>
                            <span style={{ color: 'var(--green)', flexShrink: 0 }}>✓</span>
                            {c}
                          </div>
                        ))}
                      </div>
                    </div>

                    {auditResult.recommendations?.length > 0 && (
                      <div className="card" style={{ padding: 18 }}>
                        <div style={{ fontWeight: 700, marginBottom: 10, fontSize: 13 }}>Recommendations</div>
                        {auditResult.recommendations.map((r: string) => (
                          <div key={r} style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 6 }}>→ {r}</div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ══════════ GITHUB STAGING ══════════ */}
          {tab === 'publisher' && (
            <div className="animate-fade-in">
              <div className="page-header">
                <div className="page-title">GitHub PR Staging</div>
                <div className="page-subtitle">Stage articles as pull requests against the configured site repo (needs the real pipeline)</div>
              </div>

              {!prResult ? (
                <div className="card" style={{ padding: 40, textAlign: 'center' }}>
                  <GitPullRequest size={40} color="var(--accent)" style={{ margin: '0 auto 14px' }} />
                  <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 8 }}>No PR staged yet</div>
                  <div style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 20 }}>Select a draft in the Draft Studio and click "Stage PR"</div>
                  <button className="btn-secondary" onClick={() => setTab('writer')}>Go to Draft Studio</button>
                </div>
              ) : prResult.error ? (
                <div className="card" style={{ padding: 28, maxWidth: 640, border: '1px solid rgba(220, 38, 38, 0.35)' }}>
                  <div style={{ fontWeight: 700, color: '#dc2626', marginBottom: 8 }}>PR creation failed</div>
                  <div style={{ fontSize: 13, color: 'var(--text-muted)', lineHeight: 1.5 }}>{prResult.error}</div>
                </div>
              ) : (
                <div className="card" style={{ padding: 28, maxWidth: 640 }}>
                  <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start', marginBottom: 20 }}>
                    <div style={{ padding: 10, background: 'var(--accent-light)', borderRadius: 10 }}>
                      <GitPullRequest size={22} color="var(--accent)" />
                    </div>
                    <div>
                      <div style={{ fontWeight: 700, fontSize: 16 }}>{prResult.pr_title}</div>
                      <div style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 4 }}>{prResult.target_repo} → {prResult.target_branch}</div>
                    </div>
                    <span className="badge badge-green" style={{ marginLeft: 'auto' }}>PR Ready</span>
                  </div>
                  <div className="divider" style={{ marginBottom: 16 }} />
                  {[
                    { label: 'Branch',  value: prResult.branch },
                    { label: 'Commit',  value: prResult.commit_hash },
                    { label: 'PR URL',  value: prResult.pr_url },
                  ].map(row => (
                    <div key={row.label} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12, fontSize: 13 }}>
                      <span style={{ color: 'var(--text-muted)', fontWeight: 500 }}>{row.label}</span>
                      <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-primary)', fontSize: 12 }}>{row.value}</span>
                    </div>
                  ))}
                  <div className="divider" style={{ margin: '16px 0' }} />
                  <div style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.5 }}>
                    Files staged: {prResult.files_modified?.join(', ')}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ══════════ ARCHITECTURE ══════════ */}
          {tab === 'architecture' && <Architecture statusLabel={status?.status} />}

        </div>
        <GraftStrip />
      </div>

      <div className="toasts" aria-live="polite">
        {toasts.map(t => (
          <div key={t.id} className={`toast ${t.kind}`}>{t.text}<button onClick={() => dismiss(t.id)} aria-label="Dismiss"><X size={14} /></button></div>
        ))}
      </div>

      {/* ── Sources Modal ── */}
      {sourcesModal && (
        <div
          style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.3)', zIndex: 100, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
          onClick={() => setSourcesModal(false)}
        >
          <div
            className="card"
            style={{ width: 520, maxHeight: '70vh', overflow: 'auto', padding: 24 }}
            onClick={e => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
              <div style={{ fontWeight: 700, fontSize: 15 }}>Sources for Topic</div>
              <button className="btn-ghost" onClick={() => setSourcesModal(false)}>✕</button>
            </div>
            <div style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 14 }}>{activeSourcesTopic}</div>
            <div className="divider" style={{ marginBottom: 14 }} />
            {sourcesList.length === 0 ? (
              <div style={{ textAlign: 'center', color: 'var(--text-dim)', padding: 20 }}>{sourcesLoading ? 'Loading sources…' : 'No sources recorded for this topic.'}</div>
            ) : sourcesList.map((s, i) => (
              <div key={i} style={{ marginBottom: 12, padding: '10px 14px', borderRadius: 8, background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
                <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--accent)', marginBottom: 4 }}>{s.platform}</div>
                <div style={{ fontSize: 13, fontWeight: 500 }}>{s.title}</div>
                {s.url
                  ? <a href={s.url} target="_blank" rel="noreferrer" style={{ fontSize: 11, color: 'var(--text-muted)' }}>{s.url}</a>
                  : <span style={{ fontSize: 11, color: 'var(--text-dim)' }}>no link recorded</span>}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
