import { useState } from 'react'
import { Markdown } from './Markdown'
import type { NodeState, SeoReport } from './types'

const num = (n: unknown) => (typeof n === 'number' ? n.toLocaleString() : '–')

export function SeoView({ report }: { report: SeoReport }) {
  const failing = report.checks.filter(c => !c.ok)
  const passing = report.checks.filter(c => c.ok)
  const [copied, setCopied] = useState(false)
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(report.faq_script)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1500)
    } catch {
      /* clipboard can be blocked; the text is still selectable */
    }
  }
  return (
    <div className="seo-view">
      <div className="seo-head">
        <div className={`seo-score ${report.score >= 85 ? 'good' : report.score >= 60 ? 'mid' : 'low'}`}>{report.score}</div>
        <div>
          <div className="seo-title">SEO score</div>
          <div className="muted">{report.words} words · keyword “{report.keyword || 'none'}” used {report.keyword_uses}×</div>
          <div className="muted">Slug: <code>{report.slug}</code></div>
        </div>
      </div>
      {report.meta_description && (
        <div className="seo-meta"><span className="label">Meta description</span>{report.meta_description}</div>
      )}
      {failing.length > 0 && (
        <>
          <div className="label">To fix ({failing.length})</div>
          <ul className="check-list">
            {failing.map(c => (
              <li key={c.id} className={`check fail ${c.severity}`}>
                <span className="mark">✕</span>
                <div><strong>{c.label}</strong>{c.detail && <span className="muted"> · {c.detail}</span>}
                  {c.fix && <div className="fix">{c.fix}</div>}</div>
              </li>
            ))}
          </ul>
        </>
      )}
      <div className="label">Passing ({passing.length})</div>
      <ul className="check-list">
        {passing.map(c => (
          <li key={c.id} className="check ok"><span className="mark">✓</span>
            <div>{c.label}{c.detail && <span className="muted"> · {c.detail}</span>}</div></li>
        ))}
      </ul>
      {report.rules.length > 0 && (
        <>
          <div className="label">Your rulebook ({report.rules.filter(r => r.ok).length}/{report.rules.length} followed)</div>
          <ul className="check-list">
            {report.rules.map(r => (
              <li key={r.rule_id} className={`check ${r.ok ? 'ok' : 'fail warn'}`}><span className="mark">{r.ok ? '✓' : '✕'}</span>
                <div>{r.text}<span className="muted"> · {r.detail}</span></div></li>
            ))}
          </ul>
        </>
      )}
      {report.faq_script && (
        <>
          <div className="label row">FAQ schema (JSON-LD)<button className="btn-ghost small" onClick={copy}>{copied ? 'Copied' : 'Copy'}</button></div>
          <pre className="code">{report.faq_script}</pre>
        </>
      )}
    </div>
  )
}

function KeyValues({ rows }: { rows: [string, unknown][] }) {
  return (
    <dl className="kv">
      {rows.filter(([, v]) => v !== '' && v != null).map(([k, v]) => (
        <div key={k}><dt>{k}</dt><dd>{typeof v === 'object' ? JSON.stringify(v) : String(v)}</dd></div>
      ))}
    </dl>
  )
}

function MarkdownBlock({ text }: { text: string }) {
  const [raw, setRaw] = useState(false)
  return (
    <div>
      <div className="seg"><button className={!raw ? 'on' : ''} onClick={() => setRaw(false)}>Preview</button><button className={raw ? 'on' : ''} onClick={() => setRaw(true)}>Markdown</button></div>
      {raw ? <pre className="code wrap">{text}</pre> : <Markdown source={text} />}
    </div>
  )
}

export function OutputView({ type, state }: { type: string; state: NodeState | undefined }) {
  if (!state || state.status === 'pending') return <div className="empty">Not run yet. Run this step to see its result here.</div>
  if (state.status === 'running') return <div className="empty">Running…</div>
  if (state.status === 'error') {
    return (
      <div>
        <div className="error-box">{state.error}</div>
        {state.logs.length > 0 && <div className="muted small">{state.logs.join(' · ')}</div>}
      </div>
    )
  }
  if (state.status === 'awaiting_review') return <div className="empty">Waiting for a person to approve or reject the draft.</div>
  const out = state.output ?? {}
  const logs = state.logs.length > 0 ? <div className="muted small logs">{state.logs.join(' · ')}</div> : null

  let body: React.ReactNode
  switch (type) {
    case 'topic':
      body = <KeyValues rows={[['Topic', out.topic], ['Keyword', out.keyword], ['Category', out.category], ['Notes', out.notes]]} />
      break
    case 'rss':
      body = (
        <ul className="list">
          {(out.items ?? []).map((it: any, i: number) => (
            <li key={i}><strong>{it.title}</strong><div className="muted small">{it.link}</div>{it.summary && <div className="small">{it.summary}</div>}</li>
          ))}
          {(out.errors ?? []).map((e: any, i: number) => <li key={`e${i}`} className="warn-text">{e.url}: {e.error}</li>)}
        </ul>
      )
      break
    case 'scrape':
      body = (
        <div>
          {(out.warnings ?? []).map((w: string, i: number) => <div key={i} className="note">{w}</div>)}
          {(out.serp ?? []).length > 0 && (
            <>
              <div className="label">What ranks</div>
              <ol className="list">{out.serp.map((r: any, i: number) => <li key={i}><strong>{r.title}</strong><div className="muted small">{r.url}</div></li>)}</ol>
            </>
          )}
          <div className="label">Pages read ({(out.sources ?? []).length})</div>
          <ul className="list">
            {(out.sources ?? []).map((s: any, i: number) => (
              <li key={i}><strong>{s.title || s.url}</strong><div className="muted small">{s.url}</div><div className="small clamp">{s.text}</div></li>
            ))}
          </ul>
        </div>
      )
      break
    case 'corpus':
      body = (
        <div>
          <KeyValues rows={[['Posts read', out.stats?.posts], ['Median length', out.stats?.median_words && `${out.stats.median_words} words`],
            ['Em dashes', out.stats && `${out.stats.mean_em_dash_per_1000} per 1,000 words`], ['Saved to rulebook', out.saved ? 'yes' : 'no']]} />
          <div className="label">What it learned</div>
          <ul className="list">{(out.rules ?? []).map((r: any) => <li key={r.id}>{r.text}<div className="muted small">{r.evidence}</div></li>)}</ul>
          {(out.errors ?? []).length > 0 && <div className="note">{out.errors.length} page(s) skipped: {out.errors[0].error}</div>}
        </div>
      )
      break
    case 'rulebook':
      body = (
        <div>
          <KeyValues rows={[['Rules in force', out.rule_count], ['Voice', out.voice]]} />
          <ul className="list">{(out.rules ?? []).map((r: any) => <li key={r.id}>{r.text}</li>)}</ul>
        </div>
      )
      break
    case 'keywords':
      body = (
        <div>
          <div className="primary-kw"><span className="label">Primary keyword</span>{out.primary}</div>
          {!out.has_volumes && <div className="note">This provider gives no search volumes. Use DataForSEO for real volume and difficulty.</div>}
          <table className="mini-table">
            <thead><tr><th>Keyword</th><th>Volume</th><th>Difficulty</th><th>Intent</th><th>Score</th></tr></thead>
            <tbody>
              {(out.keywords ?? []).slice(0, 25).map((k: any) => (
                <tr key={k.keyword} className={k.keyword === out.primary ? 'hl' : ''}>
                  <td>{k.keyword}</td><td>{num(k.volume)}</td><td>{k.difficulty ?? '–'}</td><td>{k.intent || '–'}</td><td>{k.score}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )
      break
    case 'outline':
      body = <MarkdownBlock text={out.outline ?? ''} />
      break
    case 'write':
      body = <div><div className="muted small">{out.draft_words} words. Open the Review step to read and edit it.</div><MarkdownBlock text={out.draft ?? ''} /></div>
      break
    case 'reddit':
      body = <MarkdownBlock text={out.reddit ?? ''} />
      break
    case 'seo':
      body = out.seo ? <SeoView report={out.seo} /> : null
      break
    case 'review':
      body = <KeyValues rows={[['Decision', out.review?.approved ? 'Approved' : 'Rejected'], ['Notes', out.review?.notes], ['Decided', out.review?.decided_at]]} />
      break
    case 'publish':
      body = <KeyValues rows={Object.entries(out.result ?? {}).filter(([k]) => k !== 'markdown') as [string, unknown][]} />
      break
    default:
      body = <pre className="code">{JSON.stringify(out, null, 2)}</pre>
  }
  return <div>{body}{logs}</div>
}
