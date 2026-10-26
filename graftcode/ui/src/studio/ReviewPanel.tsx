import { useEffect, useState } from 'react'
import { Check, RefreshCw, X } from 'lucide-react'
import { Markdown } from './Markdown'
import { SeoView } from './OutputView'
import { studio } from './api'
import { useStudio } from './StudioContext'
import type { Run, SeoReport } from './types'

interface Props {
  ws: string
  run: Run
  reviewNodeId: string
  onDecided: (run: Run, approved: boolean) => void
  onClose: () => void
}

export function ReviewPanel({ ws, run, reviewNodeId, onDecided, onClose }: Props) {
  const { fail, notify } = useStudio()
  const [markdown, setMarkdown] = useState('')
  const [saved, setSaved] = useState('')
  const [seo, setSeo] = useState<SeoReport | null>(null)
  const [tab, setTab] = useState<'draft' | 'seo' | 'reddit'>('draft')
  const [mode, setMode] = useState<'read' | 'edit'>('read')
  const [notes, setNotes] = useState('')
  const [busy, setBusy] = useState(false)
  const reddit: string | undefined = Object.values(run.nodes).map(s => s.output?.reddit).find(Boolean)

  useEffect(() => {
    let cancelled = false
    studio.draft(ws, run.id).then(d => {
      if (cancelled) return
      setMarkdown(d.markdown); setSaved(d.markdown); setSeo(d.seo)
    }).catch(fail)
    return () => { cancelled = true }
  }, [ws, run.id, fail])

  const dirty = markdown !== saved

  const saveAndCheck = async () => {
    setBusy(true)
    try {
      const d = await studio.saveDraft(ws, run.id, markdown)
      setSaved(d.markdown); setMarkdown(d.markdown); setSeo(d.seo)
      notify('Saved. The SEO report is updated.')
    } catch (e) { fail(e) } finally { setBusy(false) }
  }

  const decide = async (decision: 'approve' | 'reject') => {
    setBusy(true)
    try {
      const next = await studio.review(ws, run.id, reviewNodeId, decision, notes, dirty ? markdown : '')
      onDecided(next, decision === 'approve')
    } catch (e) { fail(e) } finally { setBusy(false) }
  }

  return (
    <aside className="drawer review">
      <div className="drawer-head">
        <div>
          <div className="drawer-title">Review the draft</div>
          <div className="muted small">{run.title || 'Untitled'} · nothing is published until you approve.</div>
        </div>
        <button className="icon-btn" onClick={onClose} aria-label="Close"><X size={16} /></button>
      </div>
      <div className="tabs">
        <button className={tab === 'draft' ? 'on' : ''} onClick={() => setTab('draft')}>Draft</button>
        <button className={tab === 'seo' ? 'on' : ''} onClick={() => setTab('seo')}>SEO{seo && <span className={`score-chip ${seo.score >= 85 ? 'good' : seo.score >= 60 ? 'mid' : 'low'}`}>{seo.score}</span>}</button>
        {reddit && <button className={tab === 'reddit' ? 'on' : ''} onClick={() => setTab('reddit')}>Reddit</button>}
      </div>
      <div className="drawer-body">
        {tab === 'draft' && (
          <div>
            <div className="row between">
              <div className="seg"><button className={mode === 'read' ? 'on' : ''} onClick={() => setMode('read')}>Read</button><button className={mode === 'edit' ? 'on' : ''} onClick={() => setMode('edit')}>Edit</button></div>
              {dirty && <button className="btn-secondary small" onClick={saveAndCheck} disabled={busy}><RefreshCw size={13} /> Save and re-check SEO</button>}
            </div>
            {mode === 'read' ? <Markdown source={markdown} /> : <textarea className="editor" value={markdown} onChange={e => setMarkdown(e.target.value)} spellCheck />}
          </div>
        )}
        {tab === 'seo' && (seo ? <SeoView report={seo} /> : <div className="empty">Loading…</div>)}
        {tab === 'reddit' && reddit && <Markdown source={reddit} />}
      </div>
      <div className="drawer-foot column">
        <input className="notes" placeholder="Note for the record (optional)" value={notes} onChange={e => setNotes(e.target.value)} />
        <div className="row">
          <button className="btn-primary" onClick={() => decide('approve')} disabled={busy}><Check size={14} /> Approve{dirty ? ' with my edits' : ''}</button>
          <button className="btn-secondary" onClick={() => decide('reject')} disabled={busy}>Reject</button>
        </div>
      </div>
    </aside>
  )
}
