import type { ReactNode } from 'react'

// A deliberately small markdown renderer. It builds React elements (never innerHTML), because the text comes
// from AI models and scraped pages and must be treated as untrusted. Only http(s) links are made clickable.

const SAFE_URL = /^https?:\/\/[^\s]+$/i

function inline(text: string, keyPrefix: string): ReactNode[] {
  const out: ReactNode[] = []
  const pattern = /(\*\*[^*\n]+\*\*|`[^`\n]+`|\[[^\]\n]*\]\([^)\s]+\)|\*[^*\n]+\*)/g
  let last = 0
  let i = 0
  for (const match of text.matchAll(pattern)) {
    const token = match[0]
    const at = match.index ?? 0
    if (at > last) out.push(text.slice(last, at))
    const key = `${keyPrefix}-${i++}`
    if (token.startsWith('**')) out.push(<strong key={key}>{token.slice(2, -2)}</strong>)
    else if (token.startsWith('`')) out.push(<code key={key}>{token.slice(1, -1)}</code>)
    else if (token.startsWith('[')) {
      const m = /^\[([^\]]*)\]\(([^)\s]+)\)$/.exec(token)
      if (m && SAFE_URL.test(m[2])) out.push(<a key={key} href={m[2]} target="_blank" rel="noreferrer noopener">{m[1] || m[2]}</a>)
      else out.push(m ? m[1] : token)
    } else out.push(<em key={key}>{token.slice(1, -1)}</em>)
    last = at + token.length
  }
  if (last < text.length) out.push(text.slice(last))
  return out
}

export function Markdown({ source }: { source: string }) {
  let body = source
  const front = /^---\n([\s\S]*?)\n---\n/.exec(source)
  if (front) body = source.slice(front[0].length)
  const lines = body.split('\n')
  const blocks: ReactNode[] = []
  let para: string[] = []
  let list: { ordered: boolean; items: string[] } | null = null
  let code: string[] | null = null
  let n = 0

  const flushPara = () => {
    if (para.length) blocks.push(<p key={`p${n++}`}>{inline(para.join(' '), `p${n}`)}</p>)
    para = []
  }
  const flushList = () => {
    if (list) {
      const Tag = list.ordered ? 'ol' : 'ul'
      blocks.push(<Tag key={`l${n++}`}>{list.items.map((it, i) => <li key={i}>{inline(it, `li${n}-${i}`)}</li>)}</Tag>)
    }
    list = null
  }

  for (const raw of lines) {
    const line = raw.trimEnd()
    if (line.trim().startsWith('```')) {
      if (code) {
        blocks.push(<pre key={`c${n++}`}><code>{code.join('\n')}</code></pre>)
        code = null
      } else {
        flushPara(); flushList()
        code = []
      }
      continue
    }
    if (code) { code.push(raw); continue }
    const heading = /^(#{1,4})\s+(.*)$/.exec(line)
    const item = /^\s*([-*+]|\d+\.)\s+(.*)$/.exec(line)
    if (heading) {
      flushPara(); flushList()
      const level = heading[1].length
      const Tag = (`h${level}`) as 'h1' | 'h2' | 'h3' | 'h4'
      blocks.push(<Tag key={`h${n++}`}>{inline(heading[2], `h${n}`)}</Tag>)
    } else if (item) {
      flushPara()
      const ordered = /\d+\./.test(item[1])
      if (!list || list.ordered !== ordered) { flushList(); list = { ordered, items: [] } }
      list.items.push(item[2])
    } else if (line.startsWith('>')) {
      flushPara(); flushList()
      blocks.push(<blockquote key={`q${n++}`}>{inline(line.replace(/^>\s?/, ''), `q${n}`)}</blockquote>)
    } else if (/^\s*<!--/.test(line) || /^-{3,}$/.test(line.trim())) {
      flushPara(); flushList()
    } else if (!line.trim()) {
      flushPara(); flushList()
    } else {
      flushList()
      para.push(line.trim())
    }
  }
  flushPara(); flushList()
  if (code) blocks.push(<pre key={`c${n++}`}><code>{(code as string[]).join('\n')}</code></pre>)
  return <div className="md">{blocks}</div>
}
