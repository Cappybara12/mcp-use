import { useState } from 'react'
import { Plus } from 'lucide-react'
import { studio } from './api'
import { useStudio } from './StudioContext'

export function WorkspaceBar() {
  const { workspaces, wsId, selectWorkspace, refreshWorkspaces, fail, notify } = useStudio()
  const [open, setOpen] = useState(false)
  const [name, setName] = useState('')
  const [site, setSite] = useState('')
  const [niche, setNiche] = useState('')
  const [template, setTemplate] = useState<'demo' | 'live'>('demo')
  const [busy, setBusy] = useState(false)

  const create = async () => {
    setBusy(true)
    try {
      const ws = await studio.createWorkspace(name.trim(), site.trim(), niche.trim(), template)
      await refreshWorkspaces()
      selectWorkspace(ws.id)
      setOpen(false); setName(''); setSite(''); setNiche('')
      notify(`Workspace “${ws.config.name}” created.`)
    } catch (e) { fail(e) } finally { setBusy(false) }
  }

  return (
    <div className="wsbar">
      <label className="wsbar-label" htmlFor="ws-select">Workspace</label>
      <div className="wsbar-row">
        <select id="ws-select" value={wsId} onChange={e => selectWorkspace(e.target.value)}>
          {workspaces.map(w => <option key={w.id} value={w.id}>{w.name}</option>)}
        </select>
        <button className="wsbar-add" onClick={() => setOpen(true)} aria-label="New workspace"><Plus size={14} /></button>
      </div>
      {open && (
        <div className="modal-back" onClick={() => setOpen(false)}>
          <div className="modal small-modal" onClick={e => e.stopPropagation()}>
            <div className="drawer-title">New workspace</div>
            <div className="muted small">One per blog or organization. Each has its own keys, rules, plan and pipelines.</div>
            <div className="field"><label className="field-label">Name</label><input autoFocus value={name} onChange={e => setName(e.target.value)} placeholder="Acme Analytics" /></div>
            <div className="field"><label className="field-label">Blog address (optional)</label><input value={site} onChange={e => setSite(e.target.value)} placeholder="https://acme.com/blog" /></div>
            <div className="field"><label className="field-label">What is it about?</label><input value={niche} onChange={e => setNiche(e.target.value)} placeholder="Product analytics for SaaS teams" /></div>
            <div className="field"><label className="field-label">Start from</label>
              <select value={template} onChange={e => setTemplate(e.target.value as 'demo' | 'live')}>
                <option value="demo">Demo: works offline with sample data</option>
                <option value="live">Live blog: your own blog and keys</option>
              </select></div>
            <div className="row between"><button className="btn-ghost" onClick={() => setOpen(false)}>Cancel</button>
              <button className="btn-primary" onClick={create} disabled={!name.trim() || busy}>{busy ? 'Creating…' : 'Create workspace'}</button></div>
          </div>
        </div>
      )}
    </div>
  )
}
