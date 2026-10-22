import { useCallback, useEffect, useRef, useState } from 'react'
import { BookOpen, Plus, Trash2 } from 'lucide-react'
import { studio } from './api'
import { useStudio } from './StudioContext'
import type { Rule, Rulebook as RulebookData } from './types'

const KIND_LABEL: Record<string, string> = {
  length: 'Length', em_dash: 'Em dashes', opener: 'Opening', hook: 'Hook', faq: 'FAQ', structure: 'Structure', title: 'Title',
  sentences: 'Sentences', lists: 'Lists', links: 'Sources', cta: 'Ending', note: 'Note', banned_phrases: 'Avoid phrases',
}

export function RulebookView() {
  const { wsId, detail, fail, notify, refreshDetail } = useStudio()
  const [rb, setRb] = useState<RulebookData | null>(null)
  const [learning, setLearning] = useState(false)
  const [editing, setEditing] = useState('')
  const [text, setText] = useState('')
  const [kind, setKind] = useState('note')
  const [phrases, setPhrases] = useState('')
  const saved = useRef('')

  const load = useCallback(async () => {
    if (!wsId) return
    try { const r = await studio.rulebook(wsId); setRb(r); saved.current = JSON.stringify(r.rules) } catch (e) { fail(e) }
  }, [wsId, fail])
  useEffect(() => { void load() }, [load])

  // save edits (toggles, rewording, deletions) shortly after they happen
  useEffect(() => {
    if (!rb || JSON.stringify(rb.rules) === saved.current) return
    const handle = window.setTimeout(async () => {
      try { const r = await studio.saveRulebook(wsId, rb); saved.current = JSON.stringify(r.rules); void refreshDetail() } catch (e) { fail(e); void load() }
    }, 500)
    return () => window.clearTimeout(handle)
  }, [rb, wsId, fail, load, refreshDetail])

  const update = (id: string, patch: Partial<Rule>) => setRb(r => r && { ...r, rules: r.rules.map(x => (x.id === id ? { ...x, ...patch } : x)) })

  const learn = async () => {
    if (!detail) return
    setLearning(true)
    try {
      for (const meta of detail.pipelines) {
        const p = await studio.pipeline(wsId, meta.id)
        const node = p.nodes.find(n => n.type === 'corpus')
        if (!node) continue
        const run = await studio.startRun(wsId, p.id, {})
        const done = await studio.runNode(wsId, run.id, node.id)
        const st = done.nodes[node.id]
        if (st.status === 'error') { fail(new Error(st.error)); return }
        notify(`Learned from ${st.output?.stats?.posts ?? 'your'} posts.`)
        await load()
        return
      }
      notify('Add a “Learn from your blog” step to a pipeline first.', 'error')
    } catch (e) { fail(e) } finally { setLearning(false) }
  }

  const addRule = async () => {
    if (!text.trim()) return
    try { setRb(await studio.addRule(wsId, text.trim(), kind, phrases)); setText(''); setPhrases(''); void refreshDetail() } catch (e) { fail(e) }
  }

  const stats = rb?.stats ?? {}
  return (
    <div className="page-pad">
      <div className="page-header row between">
        <div>
          <div className="page-title">Rulebook</div>
          <div className="page-subtitle">How this blog writes. Every draft is written to these rules and checked against them. Switch rules off, reword them, or add your own.</div>
        </div>
        <button className="btn-primary" onClick={learn} disabled={learning}><BookOpen size={14} /> {learning ? 'Reading your blog…' : 'Learn from my blog'}</button>
      </div>

      {stats.posts ? (
        <div className="stat-row">
          <div className="stat"><div className="stat-n">{stats.posts}</div><div className="muted small">posts learned from</div></div>
          <div className="stat"><div className="stat-n">{stats.median_words}</div><div className="muted small">median words</div></div>
          <div className="stat"><div className="stat-n">{stats.mean_em_dash_per_1000}</div><div className="muted small">em dashes / 1,000 words</div></div>
          <div className="stat"><div className="stat-n">{stats.median_h2}</div><div className="muted small">H2 sections</div></div>
          <div className="stat"><div className="stat-n">{stats.median_reading_ease}</div><div className="muted small">reading ease</div></div>
        </div>
      ) : (
        <div className="note">No rules learned yet. Press “Learn from my blog”: it reads your published posts and measures how you open, how long you write, whether you use em dashes, FAQs and schema, and more.</div>
      )}

      <div className="rules">
        {(rb?.rules ?? []).map(r => (
          <div key={r.id} className={`rule ${r.enabled ? '' : 'off'}`}>
            <label className="switch"><input type="checkbox" checked={r.enabled} onChange={e => update(r.id, { enabled: e.target.checked })} aria-label={`Enable rule: ${r.text}`} /><span /></label>
            <div className="rule-main">
              <div className="rule-tags"><span className="tag">{KIND_LABEL[r.kind] ?? r.kind}</span><span className={`tag ${r.source}`}>{r.source === 'custom' ? 'yours' : 'learned'}</span>{r.edited && <span className="tag">edited</span>}</div>
              {editing === r.id ? (
                <textarea autoFocus rows={2} value={r.text} onChange={e => update(r.id, { text: e.target.value, edited: true })} onBlur={() => setEditing('')} />
              ) : (
                <div className="rule-text" onClick={() => setEditing(r.id)} title="Click to reword">{r.text}</div>
              )}
              <div className="muted small">{r.evidence}</div>
            </div>
            {r.source === 'custom' && <button className="icon-btn" aria-label="Delete rule" onClick={() => setRb(x => x && { ...x, rules: x.rules.filter(y => y.id !== r.id) })}><Trash2 size={14} /></button>}
          </div>
        ))}
      </div>

      <div className="add-rule">
        <div className="label">Add your own rule</div>
        <div className="row">
          <select value={kind} onChange={e => setKind(e.target.value)} aria-label="Rule type"><option value="note">A guideline</option><option value="banned_phrases">Phrases to avoid</option></select>
          <input className="grow" placeholder={kind === 'note' ? 'e.g. Always explain jargon the first time it appears' : 'Why avoid these? e.g. Sounds like marketing'} value={text} onChange={e => setText(e.target.value)} />
        </div>
        {kind === 'banned_phrases' && <input placeholder="Phrases, separated by commas: game-changer, synergy" value={phrases} onChange={e => setPhrases(e.target.value)} />}
        <button className="btn-secondary" onClick={addRule} disabled={!text.trim()}><Plus size={14} /> Add rule</button>
      </div>

      {(rb?.sources ?? []).length > 0 && (
        <details className="sources"><summary>Posts these rules were learned from ({rb?.sources.length})</summary>
          <ul className="list">{rb?.sources.map(s => <li key={s.url}>{s.title}<div className="muted small">{s.url}</div></li>)}</ul></details>
      )}
    </div>
  )
}
