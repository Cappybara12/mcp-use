import { useEffect, useState } from 'react'
import { Link2, AlertTriangle, Globe, RefreshCw } from 'lucide-react'

interface RelatedLink {
  slug: string
  title: string
  url: string
  score: number
  included: boolean
}

interface NearDuplicate {
  title: string
  kind: 'site' | 'draft'
  ref: string
  score: number
}

interface Suggestions {
  filename: string
  engine: string
  published_as: string
  links: RelatedLink[]
  near_duplicates: NearDuplicate[]
  message: string
  error?: string
}

type Call = (method: string, body?: any) => Promise<any>

export default function RelatedReads({ filename, dirty, call, onInserted }: {
  filename: string
  dirty: boolean
  call: Call
  onInserted: () => Promise<void>
}) {
  const [data, setData] = useState<Suggestions | null>(null)
  const [picked, setPicked] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [note, setNote] = useState('')

  const load = async () => {
    if (!filename) return
    setLoading(true); setNote('')
    const r: Suggestions = await call('suggestRelatedLinks', { filename, limit: 3 })
    setData(r)
    setPicked(new Set((r?.links ?? []).map(l => l.slug)))
    setLoading(false)
  }

  useEffect(() => { setData(null); load() }, [filename])

  const toggle = (slug: string) => setPicked(prev => {
    const next = new Set(prev)
    next.has(slug) ? next.delete(slug) : next.add(slug)
    return next
  })

  const insert = async () => {
    setSaving(true)
    const slugs = (data?.links ?? []).filter(l => picked.has(l.slug)).map(l => l.slug)
    const r = await call('insertRelatedLinks', { filename, slugs: slugs.join(',') })
    setSaving(false)
    if (r?.error) { setNote(r.error); return }
    setNote(slugs.length ? `Added ${slugs.length} link${slugs.length > 1 ? 's' : ''} under "Related reads".` : 'Removed the Related reads section.')
    await onInserted()
    await load()
  }

  const sie = data?.engine?.startsWith('sie:')
  const anyIncluded = data?.links.some(l => l.included)

  return (
    <div className="card" style={{ padding: 20, marginTop: 18 }}>
      <div className="section-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Link2 size={16} color="#da1a60" />
          <span className="section-title">Related reads</span>
          <span className={`badge ${sie ? 'badge-pink' : 'badge-gray'}`}>{sie ? 'Superlinked SIE' : 'Keyword overlap'}</span>
        </div>
        <button className="btn-ghost" onClick={load} disabled={loading || !filename}>
          <RefreshCw size={13} className={loading ? 'spin' : ''} /> Refresh
        </button>
      </div>
      <p style={{ fontSize: 12.5, color: 'var(--text-muted)', margin: '4px 0 14px', lineHeight: 1.5 }}>
        Published posts on your site that this draft should link to, with their real URLs. Pick the ones you want and insert them as a "Related reads" section.
      </p>

      {loading && !data && <div style={{ fontSize: 13, color: 'var(--text-dim)' }}>Finding related posts…</div>}
      {data?.error && <div style={{ fontSize: 13, color: 'var(--red)' }}>{data.error}</div>}

      {data && !data.error && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {data.published_as && (
            <div style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: 12.5, color: 'var(--text-muted)' }}>
              <Globe size={14} color="var(--green)" />
              Already live as <code style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>{data.published_as}</code>
            </div>
          )}

          {data.near_duplicates.length > 0 && (
            <div style={{ padding: '10px 12px', borderRadius: 8, background: 'rgba(217,119,6,0.07)', border: '1px solid rgba(217,119,6,0.25)', fontSize: 12.5 }}>
              <div style={{ display: 'flex', gap: 6, alignItems: 'center', fontWeight: 700, color: 'var(--amber)', marginBottom: 4 }}>
                <AlertTriangle size={14} /> Possible duplicate{data.near_duplicates.length > 1 ? 's' : ''}
              </div>
              {data.near_duplicates.map(d => (
                <div key={d.ref} style={{ color: 'var(--text-muted)', lineHeight: 1.5 }}>
                  {d.kind === 'site' ? 'Live post' : 'Draft'} “{d.title}” <span style={{ fontFamily: 'var(--font-mono)' }}>({d.ref}, {d.score.toFixed(2)})</span>
                </div>
              ))}
            </div>
          )}

          {data.links.map(l => (
            <label key={l.slug} style={{ display: 'flex', gap: 10, alignItems: 'flex-start', padding: '10px 12px', border: '1px solid var(--border)', borderRadius: 8, cursor: 'pointer' }}>
              <input type="checkbox" checked={picked.has(l.slug)} onChange={() => toggle(l.slug)} style={{ marginTop: 3, width: 16, height: 16, flex: '0 0 auto', padding: 0 }} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 13.5, fontWeight: 600, lineHeight: 1.35 }}>{l.title}</div>
                <div style={{ fontSize: 11, color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>{l.url}</div>
              </div>
              {l.included && <span className="badge badge-green">In draft</span>}
              <span style={{ fontSize: 12, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>{l.score.toFixed(2)}</span>
            </label>
          ))}

          {data.message && <div style={{ fontSize: 12.5, color: 'var(--text-muted)' }}>{data.message}</div>}

          {(data.links.length > 0 || anyIncluded) && (
            <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginTop: 4 }}>
              <button className="btn-primary" onClick={insert} disabled={saving || dirty}>
                <Link2 size={13} /> {saving ? 'Saving…' : anyIncluded ? 'Update Related reads' : 'Insert Related reads'}
              </button>
              {dirty && <span style={{ fontSize: 12, color: 'var(--amber)' }}>Save your edits first.</span>}
            </div>
          )}
          {note && <div style={{ fontSize: 12.5, color: 'var(--green)' }}>{note}</div>}
        </div>
      )}
    </div>
  )
}
