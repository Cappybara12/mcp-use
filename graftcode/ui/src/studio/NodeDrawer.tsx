import { useState } from 'react'
import { Eye, Play, RotateCcw, Trash2, X } from 'lucide-react'
import { OutputView } from './OutputView'
import type { Catalog, NodeField, NodeState, NodeTypeInfo, PromptPreview, SecretInfo, WorkspaceConfig } from './types'

interface Props {
  info: NodeTypeInfo
  nodeId: string
  config: Record<string, any>
  state: NodeState | undefined
  catalog: Catalog
  secrets: SecretInfo[]
  wsConfig: WorkspaceConfig
  canRun: boolean
  busy: boolean
  onChange: (config: Record<string, any>) => void
  onClose: () => void
  onDelete: () => void
  onRunStep: () => void
  onRunFrom: () => void
  onPreview: () => Promise<PromptPreview | null>
  onGoToKeys: () => void
}

export function NodeDrawer(p: Props) {
  const [tab, setTab] = useState<'settings' | 'result' | 'prompt'>('settings')
  const [preview, setPreview] = useState<PromptPreview | null>(null)
  const [previewing, setPreviewing] = useState(false)

  const set = (key: string, value: unknown) => p.onChange({ ...p.config, [key]: value })
  const effectiveLlm = (p.config.provider as string) || p.wsConfig.default_provider || 'demo'

  const renderField = (f: NodeField) => {
    const value = p.config[f.key] ?? f.default ?? ''
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
            {p.info.fields.length === 0 && <div className="empty">This step has no settings.</div>}
            {p.info.fields.map(renderField)}
          </div>
        )}
        {tab === 'result' && <OutputView type={p.info.type} state={p.state} />}
        {tab === 'prompt' && (
          <div>
            <div className="field-help">This is exactly what the AI is sent. Your instructions go into “Additional instructions”; the rulebook, keywords and research are added automatically.</div>
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
