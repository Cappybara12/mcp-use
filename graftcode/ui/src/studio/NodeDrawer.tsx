import { useState } from 'react'
import { Eye, KeyRound, Play, RotateCcw, Trash2, X } from 'lucide-react'
import { OutputView } from './OutputView'
import type { Catalog, NodeField, NodeState, NodeTypeInfo, PromptPreview, SecretInfo, Template, WorkspaceConfig } from './types'

interface Props {
  info: NodeTypeInfo
  nodeId: string
  config: Record<string, any>
  state: NodeState | undefined
  catalog: Catalog
  secrets: SecretInfo[]
  wsConfig: WorkspaceConfig
  templates: Template[]
  canRun: boolean
  busy: boolean
  onChange: (config: Record<string, any>) => void
  onClose: () => void
  onDelete: () => void
  onRunStep: () => void
  onRunFrom: () => void
  onPreview: () => Promise<PromptPreview | null>
  onGoToKeys: () => void
  onSaveTemplate: (template: Partial<Template> & Pick<Template, 'name' | 'kind' | 'payload'>) => Promise<void>
}

export function NodeDrawer(p: Props) {
  const [tab, setTab] = useState<'settings' | 'result' | 'prompt'>('settings')
  const [preview, setPreview] = useState<PromptPreview | null>(null)
  const [previewing, setPreviewing] = useState(false)
  const [templateId, setTemplateId] = useState('')
  const [templateName, setTemplateName] = useState('')

  const set = (key: string, value: unknown) => p.onChange({ ...p.config, [key]: value })
  const effectiveLlm = (p.config.provider as string) || p.wsConfig.default_provider || 'demo'

  // Keep the key guidance visible before a user reaches a provider-specific field.
  // Some nodes have an optional provider, so only show a hard requirement when the
  // current configuration actually selects the keyed mode.
  const keyRequirements = (() => {
    const providers = new Set<string>()
    for (const f of p.info.fields) {
      if (f.type !== 'key_slot') continue
      const provider = f.keyProviderFrom ? String(p.config[f.keyProviderFrom] ?? '') : (f.keyProvider ?? effectiveLlm)
      if (!provider || ['demo', 'sample', 'manual', 'direct'].includes(provider)) continue
      if (provider === 'tinyfish' && ['sample', 'direct'].includes(String(p.config.provider ?? ''))) continue
      if (provider === 'github' && String(p.config.mode ?? 'dry_run') !== 'github_pr') continue
      providers.add(provider)
    }
    return [...providers].map(provider => ({
      provider,
      label: provider === 'github' ? 'GitHub token' : `${provider[0].toUpperCase()}${provider.slice(1)} API key`,
      saved: p.secrets.some(s => s.provider === provider),
    }))
  })()

  const renderField = (f: NodeField) => {
    const value = p.config[f.key] ?? p.info.defaults[f.key] ?? f.default ?? ''
    const label = <label className="field-label" htmlFor={`f-${f.key}`}>{f.label}</label>
    const help = f.help ? <div className="field-help">{f.help}</div> : null
    switch (f.type) {
      case 'textarea':
        return <div className="field" key={f.key}>{label}<textarea id={`f-${f.key}`} rows={f.key === 'prompt' ? 6 : 4} value={String(value)}
          placeholder={f.key === 'prompt' ? 'Write instructions in plain language…' : ''} onChange={e => set(f.key, e.target.value)} />{help}</div>
      case 'number':
        return <div className="field" key={f.key}>{label}<input id={`f-${f.key}`} type="number" value={String(value)} onChange={e => set(f.key, e.target.value === '' ? '' : Number(e.target.value))} />{help}</div>
      case 'bool':
        return <div className="field check-field" key={f.key}><label><input type="checkbox" checked={Boolean(p.config[f.key] ?? true)} onChange={e => set(f.key, e.target.checked)} /> {f.label}</label>{help}</div>
      case 'select':
        return <div className="field" key={f.key}>{label}<select id={`f-${f.key}`} value={String(value)} onChange={e => set(f.key, e.target.value)}>
          {(f.options ?? []).map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select>{help}</div>
      case 'llm_provider':
        return <div className="field" key={f.key}>{label}<select id={`f-${f.key}`} value={String(p.config.provider ?? '')} onChange={e => p.onChange({ ...p.config, provider: e.target.value, model: '', key_slot: '' })}>
          <option value="">Workspace default ({p.catalog.llm.find(l => l.id === (p.wsConfig.default_provider || 'demo'))?.label ?? 'Demo'})</option>
          {p.catalog.llm.map(l => <option key={l.id} value={l.id}>{l.label}</option>)}</select>{help}</div>
      case 'model': {
        const prov = p.catalog.llm.find(l => l.id === effectiveLlm)
        return <div className="field" key={f.key}>{label}<input id={`f-${f.key}`} list={`models-${p.nodeId}`} value={String(p.config.model ?? '')}
          placeholder={prov?.default_model ?? ''} onChange={e => set('model', e.target.value)} />
          <datalist id={`models-${p.nodeId}`}>{(prov?.models ?? []).map(m => <option key={m} value={m} />)}</datalist></div>
      }
      case 'key_slot': {
        const provider = f.keyProvider ?? (f.keyProviderFrom ? String(p.config[f.keyProviderFrom] ?? '') : effectiveLlm)
        const needsKey = !['', 'demo', 'sample', 'manual', 'direct'].includes(provider)
        if (!needsKey) return <div className="field" key={f.key}>{label}<div className="field-help">No key needed for this choice.</div></div>
        const options = p.secrets.filter(s => s.provider === provider)
        return <div className="field" key={f.key}>{label}
          <select id={`f-${f.key}`} value={String(p.config.key_slot ?? '')} onChange={e => set('key_slot', e.target.value)}>
            <option value="">Default {provider} key</option>
            {options.map(s => <option key={s.slot} value={s.slot}>{s.slot} ({s.masked})</option>)}
          </select>
          {options.length === 0 && <div className="field-help warn-text">No {provider} key saved yet. <button className="link" onClick={p.onGoToKeys}>Add one in Settings</button></div>}
          {help}</div>
      }
      default:
        return <div className="field" key={f.key}>{label}<input id={`f-${f.key}`} value={String(value)} onChange={e => set(f.key, e.target.value)} />{help}</div>
    }
  }

  const doPreview = async () => {
    setPreviewing(true)
    setPreview(await p.onPreview())
    setPreviewing(false)
  }

  const templateKind = p.info.ai ? 'prompt' : p.info.type
  const templates = p.templates.filter(t => t.kind === templateKind)
  const applyTemplate = () => {
    const template = templates.find(t => t.id === templateId)
    if (template && template.payload && typeof template.payload === 'object') p.onChange({ ...p.config, ...template.payload })
  }
  const saveTemplate = async () => {
    if (!templateName.trim()) return
    await p.onSaveTemplate({ name: templateName.trim(), kind: templateKind as Template['kind'], description: `Saved from the ${p.info.label} step.`, payload: p.config })
    setTemplateName('')
  }

  return (
    <aside className="drawer">
      <div className="drawer-head">
        <div>
          <div className="drawer-title">{p.info.label}</div>
          <div className="muted small">{p.info.description}</div>
        </div>
        <button className="icon-btn" onClick={p.onClose} aria-label="Close"><X size={16} /></button>
      </div>
      <div className="tabs">
        <button className={tab === 'settings' ? 'on' : ''} onClick={() => setTab('settings')}>Settings</button>
        <button className={tab === 'result' ? 'on' : ''} onClick={() => setTab('result')}>
          Result{p.state && p.state.status !== 'pending' && <span className={`pip ${p.state.status}`} />}
        </button>
        {p.info.ai && <button className={tab === 'prompt' ? 'on' : ''} onClick={() => setTab('prompt')}>Prompt</button>}
      </div>
      <div className="drawer-body">
        {tab === 'settings' && (
          <div>
            <div className="field check-field node-enabled">
              <label><input type="checkbox" checked={p.config.enabled !== false} onChange={e => set('enabled', e.target.checked)} /> Enabled</label>
              <div className="field-help">Turn this step off to skip it while keeping it in the pipeline. The rest of the connected flow will continue.</div>
            </div>
            {keyRequirements.length > 0 && (
              <div className={`key-guide ${keyRequirements.every(k => k.saved) ? 'ok' : ''}`}>
                <div className="key-guide-title"><KeyRound size={14} /> This step uses an external service</div>
                {keyRequirements.map(k => <div key={k.provider} className="key-guide-row">
                  <span><strong>{k.label}</strong> {k.saved ? <span className="muted">is saved</span> : <span className="warn-text">is not saved</span>}</span>
                  {!k.saved && <button className="link" onClick={p.onGoToKeys}>Add it in Settings &amp; keys</button>}
                </div>)}
                <div className="field-help">Keys stay on this computer and are only sent to the provider selected for this step. You can use the offline/demo or direct-fetch options where available.</div>
              </div>
            )}
            {templates.length > 0 && (
              <div className="template-box">
                <div className="field-label">Use a saved template</div>
                <div className="row">
                  <select className="grow" value={templateId} onChange={e => setTemplateId(e.target.value)}>
                    <option value="">Choose a {templateKind} template…</option>
                    {templates.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
                  </select>
                  <button className="btn-secondary small" onClick={applyTemplate} disabled={!templateId}>Apply</button>
                </div>
                <div className="field-help">Applying a template updates this step’s settings. You can still edit them afterward.</div>
              </div>
            )}
            <div className="template-box compact">
              <div className="field-label">Save these settings as a template</div>
              <div className="row"><input className="grow" placeholder={`e.g. My ${p.info.label} setup`} value={templateName} onChange={e => setTemplateName(e.target.value)} />
                <button className="btn-secondary small" onClick={() => void saveTemplate()} disabled={!templateName.trim()}>Save template</button></div>
              <div className="field-help">Templates are stored in this workspace and can be reused by you or exported from Settings.</div>
            </div>
            {p.info.fields.length === 0 && <div className="empty">This step has no settings.</div>}
            {p.info.fields.map(renderField)}
          </div>
        )}
        {tab === 'result' && <OutputView type={p.info.type} state={p.state} />}
        {tab === 'prompt' && (
          <div>
            <div className="field-help">The system prompt, rulebook, keywords and research are generated automatically. Add your own instructions below; they are appended to the AI prompt and saved with this node.</div>
            <div className="field">
              <label className="field-label" htmlFor={`prompt-${p.nodeId}`}>Additional instructions</label>
              <textarea id={`prompt-${p.nodeId}`} rows={7} value={String(p.config.prompt ?? '')}
                placeholder="For Reddit: lead with one useful insight, avoid hype, disclose ownership, and do not put the link in the main post."
                onChange={e => set('prompt', e.target.value)} />
              <div className="field-help">Changes save automatically. The Prompt preview below shows the combined instructions sent to the model.</div>
            </div>
            <button className="btn-secondary" onClick={doPreview} disabled={previewing}><Eye size={14} /> {previewing ? 'Building…' : 'Preview prompt'}</button>
            {preview && (
              <div className="prompt-preview">
                <div className="muted small">{preview.provider} · {preview.model}{preview.key_slot ? ` · key “${preview.key_slot}”` : ''}</div>
                {preview.missing_inputs.map((m, i) => <div className="note" key={i}>{m}</div>)}
                <div className="label">System</div><pre className="code wrap">{preview.system}</pre>
                <div className="label">User</div><pre className="code wrap">{preview.user}</pre>
              </div>
            )}
          </div>
        )}
      </div>
      <div className="drawer-foot">
        <button className="btn-primary" onClick={p.onRunStep} disabled={!p.canRun || p.busy}><Play size={14} /> Run this step</button>
        <button className="btn-secondary" onClick={p.onRunFrom} disabled={!p.canRun || p.busy} title="Clear this step and everything after it, then run them again"><RotateCcw size={14} /> Run from here</button>
        <button className="btn-ghost danger" onClick={p.onDelete} aria-label="Delete step"><Trash2 size={14} /></button>
      </div>
    </aside>
  )
}
