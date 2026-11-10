import { useState } from 'react'
import { Search, Type, Brain, Clock } from 'lucide-react'

interface Hit {
  filename: string
  title: string
  score: number
  engine: string
}

interface EngineResult {
  engine: string
  ms: number
  results: Hit[]
  available?: boolean
  message?: string
}

interface Comparison {
  query: string
  drafts_searched: number
  keyword: EngineResult
  sie: EngineResult
  error?: string
}

const EXAMPLES = [
  'quiet places to swim away from crowds',
  'temples and spiritual trips',
  'where to stay on a budget',
  'hidden nature spots',
]

type Call = (method: string, body?: any) => Promise<any>

function Column({ title, subtitle, icon, accent, data, pending }: {
  title: string
  subtitle: string
  icon: React.ReactNode
  accent: string
  data?: EngineResult
  pending: boolean
}) {
  const unavailable = data && data.available === false
  return (
    <div className="card" style={{ padding: 20, borderTop: `3px solid ${accent}`, display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12 }}>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <span style={{ color: accent }}>{icon}</span>
          <div>
            <div className="section-title">{title}</div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{subtitle}</div>
          </div>
        </div>
        {data && !unavailable && (
          <span className="badge badge-gray" style={{ display: 'inline-flex', gap: 4, alignItems: 'center', fontFamily: 'var(--font-mono)', whiteSpace: 'nowrap', flexShrink: 0 }}>
            <Clock size={11} /> {data.ms} ms
          </span>
        )}
      </div>

      {pending && <div style={{ fontSize: 13, color: 'var(--text-dim)', padding: '18px 0' }}>Searching…</div>}
      {!pending && !data && <div style={{ fontSize: 13, color: 'var(--text-dim)', padding: '18px 0' }}>Run a search to see results.</div>}
      {!pending && unavailable && (
        <div style={{ fontSize: 13, color: 'var(--text-muted)', padding: '12px 14px', background: 'var(--bg-surface)', borderRadius: 8, border: '1px solid var(--border)' }}>
          {data?.message}
        </div>
      )}
      {!pending && data && !unavailable && data.results.map((hit, i) => (
        <div key={hit.filename} style={{ display: 'flex', gap: 12, alignItems: 'flex-start', padding: '10px 12px', borderRadius: 8, border: '1px solid var(--border)', background: i === 0 ? 'var(--bg-surface)' : 'transparent' }}>
          <span style={{ fontWeight: 800, color: accent, fontSize: 15, minWidth: 18 }}>{i + 1}</span>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 13.5, fontWeight: 600, lineHeight: 1.35 }}>{hit.title}</div>
            <div style={{ fontSize: 11, color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{hit.filename}</div>
          </div>
          <span style={{ fontSize: 12, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>{hit.score.toFixed(2)}</span>
        </div>
      ))}
      {!pending && data && !unavailable && data.results.length === 0 && (
        <div style={{ fontSize: 13, color: 'var(--text-dim)' }}>No drafts to search yet.</div>
      )}
    </div>
  )
}

export default function SemanticSearch({ call }: { call: Call }) {
  const [query, setQuery] = useState(EXAMPLES[0])
  const [result, setResult] = useState<Comparison | null>(null)
  const [pending, setPending] = useState(false)

  const run = async (q = query) => {
    if (!q.trim()) return
    setQuery(q); setPending(true)
    const r = await call('compareSearchEngines', { query: q, limit: 3 })
    setResult(r); setPending(false)
  }

  const model = result?.sie.engine.replace(/^sie:/, '') ?? 'sentence-transformers/all-MiniLM-L6-v2'

  return (
    <div className="animate-fade-in">
      <div className="page-header">
        <div className="page-title">Semantic Search</div>
        <div className="page-subtitle">
          The same question, two engines: plain keyword overlap vs embeddings from a self-hosted Superlinked SIE server. One Python method, called here through Graftcode.
        </div>
      </div>

      <div className="card" style={{ padding: 18, marginBottom: 18 }}>
        <form onSubmit={e => { e.preventDefault(); run() }} style={{ display: 'flex', gap: 10 }}>
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: 8, border: '1px solid var(--border)', borderRadius: 8, padding: '0 12px', background: 'var(--bg)' }}>
            <Search size={15} color="var(--text-muted)" />
            <input
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder="Ask in plain words, e.g. quiet places to swim"
              style={{ flex: 1, border: 'none', outline: 'none', padding: '11px 0', fontSize: 14, background: 'transparent', color: 'var(--text-primary)' }}
            />
          </div>
          <button className="btn-primary" type="submit" disabled={pending || !query.trim()}>
            <Search size={14} /> {pending ? 'Searching…' : 'Compare'}
          </button>
        </form>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 12 }}>
          {EXAMPLES.map(ex => (
            <button key={ex} type="button" className="tag" style={{ cursor: 'pointer', border: '1px solid var(--border)' }} onClick={() => run(ex)} disabled={pending}>
              {ex}
            </button>
          ))}
        </div>
        {result?.error && <div style={{ marginTop: 12, fontSize: 13, color: 'var(--red)' }}>{result.error}</div>}
        {result && !result.error && (
          <div style={{ marginTop: 12, fontSize: 12, color: 'var(--text-muted)' }}>
            Searched {result.drafts_searched} drafts for “{result.query}”.
          </div>
        )}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 18 }}>
        <Column
          title="Keyword match"
          subtitle="Counts shared words. No model, no meaning."
          icon={<Type size={18} />}
          accent="#9ca3af"
          data={result && !result.error ? result.keyword : undefined}
          pending={pending}
        />
        <Column
          title="Superlinked SIE"
          subtitle={`Embeddings: ${model}, running locally`}
          icon={<Brain size={18} />}
          accent="var(--accent)"
          data={result && !result.error ? result.sie : undefined}
          pending={pending}
        />
      </div>

      <div style={{ marginTop: 16, fontSize: 12, color: 'var(--text-dim)', lineHeight: 1.6 }}>
        Embeddings by <a href="https://github.com/superlinked/sie" target="_blank" rel="noreferrer" style={{ color: 'var(--accent)' }}>Superlinked SIE</a>, open source and self-hosted.
        The first query after starting SIE downloads the model and can take about a minute.
      </div>
    </div>
  )
}
