import { useEffect, useState } from 'react'
import { KeyRound, Trash2 } from 'lucide-react'
import { studio } from './api'
import { useStudio } from './StudioContext'
import type { WorkspaceConfig } from './types'

export function SettingsView() {
  const { wsId, detail, catalog, fail, notify, refreshDetail, refreshWorkspaces, selectWorkspace } = useStudio()
  const [cfg, setCfg] = useState<WorkspaceConfig | null>(null)
  const [categories, setCategories] = useState('')
  const [slot, setSlot] = useState('')
  const [provider, setProvider] = useState('openai')
  const [key, setKey] = useState('')
  const [confirm, setConfirm] = useState('')

  useEffect(() => {
    if (detail) { setCfg(detail.config); setCategories(detail.config.categories.join(', ')) }
  }, [detail])

  if (!cfg || !detail || !catalog) return <div className="page-pad"><div className="empty">Loading…</div></div>
  const set = <K extends keyof WorkspaceConfig>(k: K, v: WorkspaceConfig[K]) => setCfg({ ...cfg, [k]: v })

  const save = async () => {
    try {
      await studio.saveConfig(wsId, {
        name: cfg.name, site_url: cfg.site_url, niche: cfg.niche, voice_prompt: cfg.voice_prompt, default_provider: cfg.default_provider,
        default_model: cfg.default_model, default_key_slot: cfg.default_key_slot, reddit_playbook: cfg.reddit_playbook,
        categories: categories.split(',').map(c => c.trim()).filter(Boolean), github: cfg.github, schedule: cfg.schedule,
      })
      notify('Settings saved.')
      await refreshDetail(); await refreshWorkspaces()
    } catch (e) { fail(e) }
  }

  const addKey = async () => {
    try {
      await studio.setSecret(wsId, slot.trim().toLowerCase(), provider, key.trim())
      setSlot(''); setKey('')
      notify('Key saved. It is stored on this computer and will not be shown again.')
      await refreshDetail()
    } catch (e) { fail(e) }
  }

  const removeWorkspace = async () => {
    try {
      await studio.deleteWorkspace(wsId)
      const list = await refreshWorkspaces()
      if (list.length) selectWorkspace(list[0].id)
      else window.location.reload()
    } catch (e) { fail(e) }
  }

  const llm = catalog.llm.find(l => l.id === cfg.default_provider)
  return (
    <div className="page-pad narrow">
      <div className="page-header"><div className="page-title">Settings</div><div className="page-subtitle">For the workspace “{detail.config.name}”. Each workspace has its own keys, rules, plan and pipelines.</div></div>

      <section className="panel">
        <h3>Blog</h3>
        <div className="row two">
          <div className="field"><label className="field-label">Name</label><input value={cfg.name} onChange={e => set('name', e.target.value)} /></div>
          <div className="field"><label className="field-label">Blog address</label><input placeholder="https://yourblog.com" value={cfg.site_url} onChange={e => set('site_url', e.target.value)} /></div>
        </div>
        <div className="field"><label className="field-label">What the blog is about</label><input value={cfg.niche} onChange={e => set('niche', e.target.value)} /></div>
        <div className="field"><label className="field-label">Voice (added to every AI prompt)</label>
          <textarea rows={3} placeholder="e.g. Write like a friendly senior engineer. Plain words. No hype." value={cfg.voice_prompt} onChange={e => set('voice_prompt', e.target.value)} /></div>
        <div className="field"><label className="field-label">Categories (comma separated)</label><input value={categories} onChange={e => setCategories(e.target.value)} /></div>
      </section>

      <section className="panel">
        <h3>Default AI</h3>
        <div className="row two">
          <div className="field"><label className="field-label">Provider</label>
            <select value={cfg.default_provider} onChange={e => setCfg({ ...cfg, default_provider: e.target.value, default_model: '', default_key_slot: '' })}>
              {catalog.llm.map(l => <option key={l.id} value={l.id}>{l.label}</option>)}</select></div>
          <div className="field"><label className="field-label">Model</label>
            <input list="ws-models" placeholder={llm?.default_model} value={cfg.default_model} onChange={e => set('default_model', e.target.value)} />
            <datalist id="ws-models">{(llm?.models ?? []).map(m => <option key={m} value={m} />)}</datalist></div>
        </div>
        {llm?.needs_key && (
          <div className="field"><label className="field-label">Key to use by default</label>
            <select value={cfg.default_key_slot} onChange={e => set('default_key_slot', e.target.value)}>
              <option value="">Any saved {llm.label} key</option>
              {detail.secrets.filter(s => s.provider === cfg.default_provider).map(s => <option key={s.slot} value={s.slot}>{s.slot} ({s.masked})</option>)}</select></div>
        )}
        <div className="field-help">Each step can override this: open a step on the Pipeline and choose another provider, model or key.</div>
      </section>

      <section className="panel">
        <h3>Publishing and Reddit</h3>
        <div className="row two">
          <div className="field"><label className="field-label">GitHub repository</label><input placeholder="owner/site" value={cfg.github.repo} onChange={e => set('github', { ...cfg.github, repo: e.target.value })} /></div>
          <div className="field"><label className="field-label">Base branch</label><input value={cfg.github.base_branch} onChange={e => set('github', { ...cfg.github, base_branch: e.target.value })} /></div>
        </div>
        <div className="field"><label className="field-label">File path ({'{slug}'} is replaced)</label><input value={cfg.github.path_template} onChange={e => set('github', { ...cfg.github, path_template: e.target.value })} /></div>
        <div className="field"><label className="field-label">How you post on Reddit</label>
          <textarea rows={6} value={cfg.reddit_playbook} onChange={e => set('reddit_playbook', e.target.value)} />
          <div className="field-help">Reddit post ideas are written around this. Describe your style, the subreddits you use, and your rules for self-promotion.</div></div>
      </section>
      <div className="row"><button className="btn-primary" onClick={save}>Save settings</button></div>

      <section className="panel">
        <h3><KeyRound size={15} /> API keys</h3>
        <div className="field-help">Keys are stored only on this computer (in <code>~/.graft-studio</code>, outside the project) and are sent only to the provider they belong to. They are never shown again after you save them.</div>
        {detail.secrets.length === 0 && <div className="empty small">No keys yet. The offline Demo AI and sample data work without one.</div>}
        <div className="keys">
          {detail.secrets.map(s => (
            <div className="key-row" key={s.slot}><strong>{s.slot}</strong><span className="tag">{s.provider}</span><code>{s.masked}</code><span className="grow" />
              <button className="icon-btn" aria-label={`Delete key ${s.slot}`} onClick={async () => { try { await studio.deleteSecret(wsId, s.slot); await refreshDetail() } catch (e) { fail(e) } }}><Trash2 size={14} /></button></div>
          ))}
        </div>
        <div className="row key-add">
          <input placeholder="Name, e.g. main" value={slot} onChange={e => setSlot(e.target.value)} />
          <select value={provider} onChange={e => setProvider(e.target.value)} aria-label="Provider">{catalog.key_providers.map(p => <option key={p}>{p}</option>)}</select>
          <input className="grow" type="password" autoComplete="off" placeholder="Paste the key" value={key} onChange={e => setKey(e.target.value)} />
          <button className="btn-secondary" onClick={addKey} disabled={!slot.trim() || !key.trim()}>Save key</button>
        </div>
        <div className="field-help">Can't paste into the box above? In a terminal, run <code>bash scripts/add-key.sh {wsId} openai --default</code> (from the <code>graftcode</code> folder). It asks for the key with hidden input and saves it here.</div>
        <div className="field-help">For DataForSEO (the data OpenSEO uses), paste the Base64 value from its API Access page or <code>login:password</code>. TinyFish keys come from agent.tinyfish.ai.</div>
      </section>

      <section className="panel danger-zone">
        <h3>Delete this workspace</h3>
        <div className="field-help">Removes its keys, rules, plan, pipelines and drafts from this computer. This cannot be undone.</div>
        <div className="row"><input placeholder={`Type “${detail.config.name}” to confirm`} value={confirm} onChange={e => setConfirm(e.target.value)} />
          <button className="btn-secondary danger" onClick={removeWorkspace} disabled={confirm !== detail.config.name}>Delete workspace</button></div>
      </section>
    </div>
  )
}
