import { useCallback, useEffect, useMemo, useState } from 'react'
import { CalendarClock, ChevronLeft, ChevronRight, Copy, GitBranch, Plus, Sparkles, Trash2, X } from 'lucide-react'
import { studio } from './api'
import { useStudio } from './StudioContext'
import type { Idea, PlanItem } from './types'

const DRAG_IDEA = 'application/graft-idea'
const DRAG_ITEM = 'application/graft-plan-item'

const pad = (n: number) => String(n).padStart(2, '0')
const dayKey = (d: Date) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
const toLocalInput = (iso: string) => {
  if (!iso) return ''
  const d = new Date(iso)
  return `${dayKey(d)}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}
const timeLabel = (iso: string) => { const d = new Date(iso); return `${pad(d.getHours())}:${pad(d.getMinutes())}` }
const atNine = (day: Date) => new Date(day.getFullYear(), day.getMonth(), day.getDate(), 9, 0).toISOString()

function monthGrid(year: number, month: number): Date[] {
  const first = new Date(year, month, 1)
  const offset = (first.getDay() + 6) % 7                       // weeks start on Monday
  return Array.from({ length: 42 }, (_, i) => new Date(year, month, 1 - offset + i))
}

const STATUS_LABEL: Record<string, string> = {
  idea: 'Idea', planned: 'Planned', drafting: 'Drafting', review: 'Needs review', approved: 'Approved', published: 'Published', rejected: 'Rejected',
}

export function Planner({ onOpenPipeline }: { onOpenPipeline: () => void }) {
  const { wsId, detail, fail, notify, refreshDetail } = useStudio()
  const [ideas, setIdeas] = useState<Idea[]>([])
  const [plan, setPlan] = useState<PlanItem[]>([])
  const [cursor, setCursor] = useState(() => { const t = new Date(); return new Date(t.getFullYear(), t.getMonth(), 1) })
  const [filter, setFilter] = useState('All')
  const [newTitle, setNewTitle] = useState('')
  const [newKeyword, setNewKeyword] = useState('')
  const [newCategory, setNewCategory] = useState('')
  const [editing, setEditing] = useState<PlanItem | null>(null)
  const [overDay, setOverDay] = useState('')
  const [creating, setCreating] = useState<{ title: string; step: string } | null>(null)
  const [scheduleOpen, setScheduleOpen] = useState(false)
  const [today] = useState(() => dayKey(new Date()))

  const categories = detail?.config.categories ?? []
  const pipelineId = detail?.pipelines[0]?.id ?? ''

  const load = useCallback(async () => {
    if (!wsId) return
    try {
      const [i, p] = await Promise.all([studio.ideas(wsId), studio.plan(wsId)])
      setIdeas(i); setPlan(p)
    } catch (e) { fail(e) }
  }, [wsId, fail])
  useEffect(() => { void load() }, [load])

  const grid = useMemo(() => monthGrid(cursor.getFullYear(), cursor.getMonth()), [cursor])
  const byDay = useMemo(() => {
    const m = new Map<string, PlanItem[]>()
    for (const it of plan) if (it.scheduled_for) { const k = dayKey(new Date(it.scheduled_for)); m.set(k, [...(m.get(k) ?? []), it]) }
    for (const list of m.values()) list.sort((a, b) => a.scheduled_for.localeCompare(b.scheduled_for))
    return m
  }, [plan])

  const shownIdeas = ideas.filter(i => filter === 'All' || i.category === filter)
  const unscheduled = plan.filter(p => !p.scheduled_for && p.status === 'idea')
  const scheduledItems = plan.filter(p => p.scheduled_for).sort((a, b) => a.scheduled_for.localeCompare(b.scheduled_for))

  const savePlan = async (item: Partial<PlanItem>) => {
    try {
      const saved = await studio.savePlanItem(wsId, item)
      setPlan(await studio.plan(wsId))
      return saved
    } catch (e) { fail(e); return null }
  }

  const addIdea = async () => {
    if (!newTitle.trim()) return
    try {
      setIdeas(await studio.addIdea(wsId, newTitle.trim(), newKeyword.trim(), newCategory))
      setNewTitle(''); setNewKeyword('')
    } catch (e) { fail(e) }
  }

  const onDropDay = async (e: React.DragEvent, day: Date) => {
    e.preventDefault()
    setOverDay('')
    const itemRaw = e.dataTransfer.getData(DRAG_ITEM)
    const ideaRaw = e.dataTransfer.getData(DRAG_IDEA)
    if (itemRaw) {
      const it: PlanItem = JSON.parse(itemRaw)
      const when = new Date(it.scheduled_for || atNine(day))
      const moved = new Date(day.getFullYear(), day.getMonth(), day.getDate(), when.getHours(), when.getMinutes()).toISOString()
      await savePlan({ id: it.id, title: it.title, scheduled_for: moved, status: it.status === 'idea' ? 'planned' : it.status })
    } else if (ideaRaw) {
      const idea: Idea = JSON.parse(ideaRaw)
      await savePlan({ title: idea.title, keyword: idea.keyword, category: idea.category, source: idea.source, scheduled_for: atNine(day), status: 'planned' })
    }
  }

  const createDraft = async (item: PlanItem) => {
    if (!pipelineId) return
    setEditing(null)
    setCreating({ title: item.title, step: 'Starting…' })
    try {
      let run = await studio.startRunForPlanItem(wsId, item.pipeline_id || pipelineId, item.id)
      for (const nid of run.order) {
        if (run.nodes[nid]?.status !== 'pending') continue
        setCreating({ title: item.title, step: nid })
        run = await studio.runNode(wsId, run.id, nid)
        const st = run.nodes[nid].status
        if (st === 'error') { fail(new Error(`${nid}: ${run.nodes[nid].error}`)); break }
        if (st === 'awaiting_review') { notify('Draft ready. Open the pipeline to review it.'); break }
      }
    } catch (e) { fail(e) } finally {
      setCreating(null)
      await load()
      void refreshDetail()
    }
  }

  const runDue = async () => {
    try {
      const results = await studio.runDue(wsId)
      notify(results.length ? `Created ${results.filter(r => r.ok).length} draft(s) from ${results.length} due item(s).` : 'Nothing is due yet.')
      await load()
    } catch (e) { fail(e) }
  }

  const monthName = cursor.toLocaleString(undefined, { month: 'long', year: 'numeric' })

  return (
    <div className="planner">
      <aside className="library">
        <div className="palette-title">Content library</div>
        <div className="palette-hint">Drag an idea onto a day to schedule it.</div>
        <div className="chips">
          {['All', ...categories].map(c => <button key={c} className={`chip ${filter === c ? 'on' : ''}`} onClick={() => setFilter(c)}>{c}</button>)}
        </div>
        <div className="idea-add">
          <input placeholder="Add an idea…" value={newTitle} onChange={e => setNewTitle(e.target.value)} onKeyDown={e => e.key === 'Enter' && addIdea()} />
          <div className="row">
            <input placeholder="Keyword" value={newKeyword} onChange={e => setNewKeyword(e.target.value)} />
            <select value={newCategory} onChange={e => setNewCategory(e.target.value)} aria-label="Category"><option value="">No category</option>{categories.map(c => <option key={c}>{c}</option>)}</select>
          </div>
          <button className="btn-secondary small" onClick={addIdea} disabled={!newTitle.trim()}><Plus size={13} /> Add</button>
        </div>
        <div className="ideas">
          {shownIdeas.length === 0 && <div className="empty small">No ideas yet. Run a pipeline with RSS or keyword research, or add one above.</div>}
          {shownIdeas.map(i => (
            <div key={i.id} className="idea" draggable onDragStart={e => { e.dataTransfer.setData(DRAG_IDEA, JSON.stringify(i)); e.dataTransfer.effectAllowed = 'copyMove' }}>
              <div className="idea-title">{i.title}</div>
              <div className="idea-meta"><span className="tag">{i.source}</span>{i.keyword && <span className="muted small">{i.keyword}</span>}{i.category && <span className="muted small">· {i.category}</span>}</div>
              <button className="icon-btn tiny del" aria-label="Remove idea" onClick={async () => { try { setIdeas(await studio.deleteIdea(wsId, i.id)) } catch (e) { fail(e) } }}><X size={12} /></button>
            </div>
          ))}
        </div>
        {unscheduled.length > 0 && (
          <>
            <div className="label">Unscheduled</div>
            {unscheduled.map(p => (
              <div key={p.id} className="idea" draggable onDragStart={e => { e.dataTransfer.setData(DRAG_ITEM, JSON.stringify(p)); e.dataTransfer.effectAllowed = 'move' }} onClick={() => setEditing(p)}>
                <div className="idea-title">{p.title}</div>
              </div>
            ))}
          </>
        )}
      </aside>

      <section className="calendar-col">
        <div className="toolbar">
          <button className="icon-btn" onClick={() => setCursor(new Date(cursor.getFullYear(), cursor.getMonth() - 1, 1))} aria-label="Previous month"><ChevronLeft size={16} /></button>
          <div className="month">{monthName}</div>
          <button className="icon-btn" onClick={() => setCursor(new Date(cursor.getFullYear(), cursor.getMonth() + 1, 1))} aria-label="Next month"><ChevronRight size={16} /></button>
          <button className="btn-ghost small" onClick={() => { const t = new Date(); setCursor(new Date(t.getFullYear(), t.getMonth(), 1)) }}>Today</button>
          <span className="grow" />
          <button className="btn-secondary small" onClick={runDue}><Sparkles size={13} /> Create drafts that are due</button>
          <button className="btn-primary small" onClick={() => setScheduleOpen(true)}><GitBranch size={13} /> Schedule on GitHub</button>
        </div>
        <div className="cal">
          {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map(d => <div key={d} className="cal-dow">{d}</div>)}
          {grid.map(day => {
            const key = dayKey(day)
            const inMonth = day.getMonth() === cursor.getMonth()
            return (
              <div key={key} className={`cal-day ${inMonth ? '' : 'out'} ${key === today ? 'today' : ''} ${overDay === key ? 'over' : ''}`}
                onDragOver={e => { e.preventDefault(); setOverDay(key) }} onDragLeave={() => setOverDay(o => (o === key ? '' : o))} onDrop={e => onDropDay(e, day)}>
                <div className="cal-num">{day.getDate()}</div>
                {(byDay.get(key) ?? []).map(it => (
                  <div key={it.id} className={`cal-item ${it.status}`} draggable title={`${STATUS_LABEL[it.status] ?? it.status}: ${it.title}`}
                    onDragStart={e => { e.dataTransfer.setData(DRAG_ITEM, JSON.stringify(it)); e.dataTransfer.effectAllowed = 'move' }} onClick={() => setEditing(it)}>
                    <span className="cal-time">{timeLabel(it.scheduled_for)}</span> {it.title}
                  </div>
                ))}
              </div>
            )
          })}
        </div>
        <div className="plan-list">
          <div className="label">Scheduled ({scheduledItems.length})</div>
          {scheduledItems.length === 0 && <div className="empty small">Nothing scheduled. Drag ideas onto the calendar.</div>}
          {scheduledItems.map(it => (
            <div key={it.id} className="plan-row" onClick={() => setEditing(it)}>
              <CalendarClock size={14} /><span className="plan-when">{new Date(it.scheduled_for).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })}</span>
              <span className="plan-title">{it.title}</span><span className={`status-pill ${it.status}`}>{STATUS_LABEL[it.status] ?? it.status}</span>
            </div>
          ))}
        </div>
      </section>

      {editing && <ItemEditor item={editing} categories={categories} pipelines={detail?.pipelines ?? []} onClose={() => setEditing(null)}
        onSave={async patch => { const s = await savePlan({ ...patch, id: editing.id }); if (s) setEditing(null) }}
        onDelete={async () => { try { setPlan(await studio.deletePlanItem(wsId, editing.id)); setEditing(null) } catch (e) { fail(e) } }}
        onCreate={() => createDraft(editing)} onOpenPipeline={() => { setEditing(null); onOpenPipeline() }} />}

      {creating && (
        <div className="modal-back"><div className="modal small-modal">
          <div className="drawer-title">Creating a draft</div>
          <div className="muted">“{creating.title}”</div>
          <div className="progress"><span className="spin dotpulse" /> Step: <strong>{creating.step}</strong></div>
        </div></div>
      )}
      {scheduleOpen && <ScheduleModal ws={wsId} cron={detail?.config.schedule.cron ?? '0 9 * * 1-5'} onClose={() => setScheduleOpen(false)} />}
    </div>
  )
}

function ItemEditor({ item, categories, pipelines, onClose, onSave, onDelete, onCreate, onOpenPipeline }: {
  item: PlanItem; categories: string[]; pipelines: { id: string; name: string }[]
  onClose: () => void; onSave: (patch: Partial<PlanItem>) => void; onDelete: () => void; onCreate: () => void; onOpenPipeline: () => void
}) {
  const [title, setTitle] = useState(item.title)
  const [keyword, setKeyword] = useState(item.keyword)
  const [category, setCategory] = useState(item.category)
  const [notes, setNotes] = useState(item.notes)
  const [when, setWhen] = useState(toLocalInput(item.scheduled_for))
  const [pipeline, setPipeline] = useState(item.pipeline_id)
  const canDraft = ['idea', 'planned', 'rejected'].includes(item.status) || !item.run_id
  return (
    <div className="modal-back" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="drawer-head"><div><div className="drawer-title">Plan item</div><span className={`status-pill ${item.status}`}>{STATUS_LABEL[item.status] ?? item.status}</span></div>
          <button className="icon-btn" onClick={onClose} aria-label="Close"><X size={16} /></button></div>
        <div className="field"><label className="field-label">Title</label><input value={title} onChange={e => setTitle(e.target.value)} /></div>
        <div className="row two">
          <div className="field"><label className="field-label">Primary keyword</label><input value={keyword} onChange={e => setKeyword(e.target.value)} /></div>
          <div className="field"><label className="field-label">Category</label><select value={category} onChange={e => setCategory(e.target.value)}><option value="">None</option>{categories.map(c => <option key={c}>{c}</option>)}</select></div>
        </div>
        <div className="row two">
          <div className="field"><label className="field-label">Create the draft at</label><input type="datetime-local" value={when} onChange={e => setWhen(e.target.value)} /></div>
          <div className="field"><label className="field-label">Pipeline</label><select value={pipeline} onChange={e => setPipeline(e.target.value)}><option value="">First pipeline</option>{pipelines.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}</select></div>
        </div>
        <div className="field"><label className="field-label">Notes for the writer</label><textarea rows={3} value={notes} onChange={e => setNotes(e.target.value)} /></div>
        <div className="row between">
          <button className="btn-ghost danger" onClick={onDelete}><Trash2 size={14} /> Delete</button>
          <div className="row">
            {item.status === 'review' && <button className="btn-secondary" onClick={onOpenPipeline}>Open review</button>}
            {canDraft && <button className="btn-secondary" onClick={onCreate}><Sparkles size={14} /> Create draft now</button>}
            <button className="btn-primary" onClick={() => onSave({ title, keyword, category, notes, pipeline_id: pipeline, scheduled_for: when ? new Date(when).toISOString() : '', status: when && item.status === 'idea' ? 'planned' : item.status })}>Save</button>
          </div>
        </div>
      </div>
    </div>
  )
}

function ScheduleModal({ ws, cron: initial, onClose }: { ws: string; cron: string; onClose: () => void }) {
  const { fail, notify } = useStudio()
  const [cron, setCron] = useState(initial)
  const [out, setOut] = useState<Awaited<ReturnType<typeof studio.exportWorkflow>> | null>(null)
  const [bundle, setBundle] = useState<{ path: string; content: string }[]>([])
  const generate = async () => {
    try {
      setOut(await studio.exportWorkflow(ws, cron))
      setBundle((await studio.exportBundle(ws)).files)
    } catch (e) { fail(e) }
  }
  useEffect(() => { void generate() }, []) // eslint-disable-line react-hooks/exhaustive-deps
  const copy = async (text: string) => { try { await navigator.clipboard.writeText(text); notify('Copied.') } catch { notify('Copy was blocked by the browser. Select the text instead.', 'error') } }
  return (
    <div className="modal-back" onClick={onClose}>
      <div className="modal wide" onClick={e => e.stopPropagation()}>
        <div className="drawer-head"><div><div className="drawer-title">Schedule on GitHub</div>
          <div className="muted small">A GitHub Action creates drafts for items that are due and opens a pull request. You review and merge; nothing publishes by itself.</div></div>
          <button className="icon-btn" onClick={onClose} aria-label="Close"><X size={16} /></button></div>
        <div className="field"><label className="field-label">When to run (cron, UTC)</label>
          <div className="row"><input value={cron} onChange={e => setCron(e.target.value)} /><button className="btn-secondary" onClick={generate}>Update</button></div>
          <div className="field-help">Example: <code>0 9 * * 1-5</code> is 09:00 UTC on weekdays.</div></div>
        {out && (
          <>
            <ol className="how">{out.steps.map((s, i) => <li key={i}>{s}</li>)}</ol>
            {out.secrets_needed.length > 0 && <div className="note">Add these repository secrets: {out.secrets_needed.map(s => <code key={s.name}>{s.name}</code>)}</div>}
            <div className="label row between">{out.path}<button className="btn-ghost small" onClick={() => copy(out.yaml)}><Copy size={13} /> Copy</button></div>
            <pre className="code">{out.yaml}</pre>
            <div className="label">Workspace files to commit (no API keys are included)</div>
            {bundle.map(f => <div key={f.path} className="file-row"><code>{f.path}</code><button className="btn-ghost small" onClick={() => copy(f.content)}><Copy size={13} /> Copy</button></div>)}
          </>
        )}
      </div>
    </div>
  )
}
