import { useEffect, useMemo, useState } from 'react'
import { FlaskConical, RefreshCw, Check, X } from 'lucide-react'

// Validated pair (categorical checks + colour-blind separation pass on the light surface).
const KEYWORD = '#3b6fd4'
const SIE = '#da1a60'

interface Score { accuracy: number; precision?: number; recall?: number; correct: number; total: number }
interface SweepPoint extends Score { value: number }
interface Task {
  id: 'on_brand' | 'covered' | 'category'
  name: string
  positive: string
  keyword_rule: string
  keyword: Score
  sie?: Score
  threshold?: { name: string; value: number }
  sweep?: SweepPoint[]
  variants?: (Score & { name: string })[]
}
interface Answer { on_brand: boolean; covered: boolean; category: string }
interface Item {
  topic: string
  label: Answer
  keyword: Answer
  sie?: Answer & { relevance: number; covered_score: number; closest_draft: string }
}
interface Report {
  labels_file: string
  labelled: number
  drafts: number
  engine: string
  sie_available: boolean
  sie_ms: number
  message: string
  tasks: Task[]
  items: Item[]
  error?: string
}

type Call = (method: string, body?: any) => Promise<any>

const pct = (x: number) => `${Math.round(x * 100)}%`

function Legend() {
  return (
    <div style={{ display: 'flex', gap: 16, fontSize: 12, color: 'var(--text-muted)' }}>
      {[['Keyword matching', KEYWORD], ['Superlinked SIE', SIE]].map(([label, color]) => (
        <span key={label} style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
          <span style={{ width: 10, height: 10, borderRadius: 3, background: color }} />{label}
        </span>
      ))}
    </div>
  )
}

function ScoreBar({ label, color, score }: { label: string; color: string; score?: Score }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '78px 1fr 92px', alignItems: 'center', gap: 10 }}>
      <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{label}</span>
      <div style={{ height: 12, background: 'var(--bg-surface)', borderRadius: 4, overflow: 'hidden' }}>
        {score && (
          <div
            title={`${label}: ${score.correct} of ${score.total} correct`}
            style={{ width: `${score.accuracy * 100}%`, height: '100%', background: color, borderRadius: '0 4px 4px 0' }}
          />
        )}
      </div>
      <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)', textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>
        {score ? pct(score.accuracy) : '—'}
        {score && <span style={{ fontWeight: 400, color: 'var(--text-dim)', fontSize: 11 }}> {score.correct}/{score.total}</span>}
      </span>
    </div>
  )
}

function TaskCard({ task }: { task: Task }) {
  const binary = task.id !== 'category'
  return (
    <div className="card" style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div>
        <div className="section-title">{task.name}</div>
        <div style={{ fontSize: 11.5, color: 'var(--text-dim)', marginTop: 2 }}>Keyword rule: {task.keyword_rule}</div>
      </div>
      <ScoreBar label="Keyword" color={KEYWORD} score={task.keyword} />
      <ScoreBar label="SIE" color={SIE} score={task.sie} />
      {binary && (
        <div style={{ fontSize: 11.5, color: 'var(--text-muted)', lineHeight: 1.6, fontVariantNumeric: 'tabular-nums' }}>
          Finds {task.positive} topics (recall): keyword {pct(task.keyword.recall ?? 0)}{task.sie && <> · SIE {pct(task.sie.recall ?? 0)}</>}
          <br />
          Right when it says {task.positive} (precision): keyword {pct(task.keyword.precision ?? 0)}{task.sie && <> · SIE {pct(task.sie.precision ?? 0)}</>}
        </div>
      )}
      {task.variants && (
        <div style={{ fontSize: 11.5, color: 'var(--text-muted)', lineHeight: 1.7 }}>
          {task.variants.map(v => (
            <div key={v.name} style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>{v.name}</span><span style={{ fontVariantNumeric: 'tabular-nums', color: 'var(--text-primary)' }}>{pct(v.accuracy)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function Sweep({ task }: { task: Task }) {
  if (!task.sweep || !task.threshold) return null
  const H = 120
  return (
    <div className="card" style={{ padding: 20 }}>
      <div className="section-title">{task.name}: SIE accuracy by threshold</div>
      <div style={{ fontSize: 11.5, color: 'var(--text-dim)', margin: '2px 0 14px' }}>
        <code style={{ fontFamily: 'var(--font-mono)' }}>semantic.{task.threshold.name}</code> is {task.threshold.value} (outlined). Hover a bar for precision and recall.
      </div>
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: 2, height: H + 34 }}>
        {task.sweep.map(p => {
          const current = Math.abs(p.value - task.threshold!.value) < 1e-9
          return (
            <div key={p.value} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}
              title={`${task.threshold!.name} ${p.value}: accuracy ${pct(p.accuracy)}, precision ${pct(p.precision ?? 0)}, recall ${pct(p.recall ?? 0)}`}>
              <span style={{ fontSize: 11, color: current ? 'var(--text-primary)' : 'var(--text-muted)', fontWeight: current ? 700 : 400, fontVariantNumeric: 'tabular-nums' }}>
                {pct(p.accuracy)}
              </span>
              <div style={{
                width: '100%', maxWidth: 34, height: Math.max(2, p.accuracy * H), background: SIE,
                opacity: current ? 1 : 0.45, borderRadius: '4px 4px 0 0',
                outline: current ? '2px solid var(--text-primary)' : 'none', outlineOffset: 2,
              }} />
              <span style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>{p.value}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function Cell({ ok, text }: { ok: boolean; text: string }) {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, color: ok ? 'var(--text-primary)' : 'var(--red)' }}>
      {ok ? <Check size={13} color="var(--green)" aria-label="correct" /> : <X size={13} aria-label="wrong" />}
      {text}
    </span>
  )
}

export default function Evaluation({ call }: { call: Call }) {
  const [report, setReport] = useState<Report | null>(null)
  const [loading, setLoading] = useState(false)
  const [onlyMistakes, setOnlyMistakes] = useState(true)

  const run = async () => {
    setLoading(true)
    setReport(await call('evaluateSemanticEngine'))
    setLoading(false)
  }
  useEffect(() => { run() }, [])

  const rows = useMemo(() => {
    if (!report?.items) return []
    return report.items.filter(i => {
      if (!onlyMistakes) return true
      const wrong = (a?: Answer) => !!a && (a.on_brand !== i.label.on_brand || a.covered !== i.label.covered || a.category !== i.label.category)
      return wrong(i.keyword) || wrong(i.sie)
    })
  }, [report, onlyMistakes])

  const yesNo = (b: boolean, yes: string, no: string) => (b ? yes : no)

  return (
    <div className="animate-fade-in">
      <div className="page-header">
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16 }}>
          <div>
            <div className="page-title">Evaluation</div>
            <div className="page-subtitle">
              Keyword matching vs Superlinked SIE on topics labelled by hand. Change a threshold or model in the config, restart, and run again to compare.
            </div>
          </div>
          <button className="btn-primary" onClick={run} disabled={loading}>
            <RefreshCw size={14} className={loading ? 'spin' : ''} /> {loading ? 'Running…' : 'Run evaluation'}
          </button>
        </div>
      </div>

      {loading && !report && <div className="card" style={{ padding: 24, fontSize: 13, color: 'var(--text-dim)' }}>Scoring labelled topics…</div>}
      {report?.error && <div className="card" style={{ padding: 20, color: 'var(--red)', fontSize: 13 }}>{report.error}</div>}

      {report && !report.error && (
        <>
          <div className="card" style={{ padding: '12px 18px', marginBottom: 18, display: 'flex', flexWrap: 'wrap', gap: 18, alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', gap: 10, alignItems: 'center', fontSize: 12.5, color: 'var(--text-muted)', flexWrap: 'wrap' }}>
              <FlaskConical size={15} color={SIE} />
              <span><strong style={{ color: 'var(--text-primary)' }}>{report.labelled}</strong> labelled topics</span>
              <span>· {report.drafts} drafts</span>
              <span>· {report.sie_available ? <>model <code style={{ fontFamily: 'var(--font-mono)' }}>{report.engine.replace(/^sie:/, '')}</code> · {report.sie_ms} ms</> : 'SIE offline'}</span>
            </div>
            <Legend />
          </div>
          {report.message && <div style={{ fontSize: 12.5, color: 'var(--amber)', marginBottom: 14 }}>{report.message}</div>}

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 16, marginBottom: 16 }}>
            {report.tasks.map(t => <TaskCard key={t.id} task={t} />)}
          </div>

          {report.sie_available && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: 16, marginBottom: 16 }}>
              {report.tasks.filter(t => t.sweep).map(t => <Sweep key={t.id} task={t} />)}
            </div>
          )}

          <div className="card" style={{ padding: 20 }}>
            <div className="section-header">
              <span className="section-title">Topics ({rows.length} of {report.items.length})</span>
              <label style={{ display: 'flex', gap: 6, alignItems: 'center', fontSize: 12, color: 'var(--text-muted)', cursor: 'pointer' }}>
                <input type="checkbox" checked={onlyMistakes} onChange={e => setOnlyMistakes(e.target.checked)} style={{ width: 14, height: 14, padding: 0 }} />
                Only topics where an engine is wrong
              </label>
            </div>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', fontSize: 12.5, borderCollapse: 'collapse' }}>
                <thead>
                  <tr>
                    {['Topic', 'Label', 'Keyword', 'Superlinked SIE'].map(h => (
                      <th key={h} style={{ textAlign: 'left', padding: '8px 10px', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rows.map(i => (
                    <tr key={i.topic} style={{ borderTop: '1px solid var(--border)', verticalAlign: 'top' }}>
                      <td style={{ padding: '9px 10px', maxWidth: 320, fontWeight: 500 }}>{i.topic}</td>
                      <td style={{ padding: '9px 10px', color: 'var(--text-muted)', lineHeight: 1.6, whiteSpace: 'nowrap' }}>
                        {yesNo(i.label.on_brand, 'On-brand', 'Off-brand')}<br />{yesNo(i.label.covered, 'Covered', 'New')}<br />{i.label.category}
                      </td>
                      {[i.keyword, i.sie].map((a, n) => (
                        <td key={n} style={{ padding: '9px 10px', lineHeight: 1.6, whiteSpace: 'nowrap' }}>
                          {a ? (
                            <>
                              <Cell ok={a.on_brand === i.label.on_brand} text={yesNo(a.on_brand, 'On-brand', 'Off-brand') + (n && i.sie ? ` (${i.sie.relevance.toFixed(2)})` : '')} /><br />
                              <Cell ok={a.covered === i.label.covered} text={yesNo(a.covered, 'Covered', 'New') + (n && i.sie ? ` (${i.sie.covered_score.toFixed(2)})` : '')} /><br />
                              <Cell ok={a.category === i.label.category} text={a.category} />
                            </>
                          ) : <span style={{ color: 'var(--text-dim)' }}>—</span>}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div style={{ fontSize: 11.5, color: 'var(--text-dim)', marginTop: 12 }}>
              Labels: <code style={{ fontFamily: 'var(--font-mono)' }}>{report.labels_file}</code>. The keyword lists were written while looking at these same topics, so the keyword scores here are, if anything, generous.
            </div>
          </div>
        </>
      )}
    </div>
  )
}
