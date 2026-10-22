import { ArticlePipelineService, GraftConfig } from 'graft-client'

// The browser talks to the Graftcode Gateway directly: no HTTP adapter in between.
const GRAFT_WS = import.meta.env.VITE_GRAFT_HOST ?? 'ws://localhost:8080/ws'
const MCP_URL = import.meta.env.VITE_GRAFT_MCP_URL ?? 'http://localhost:8081/mcp'

GraftConfig.host = GRAFT_WS
const service = new ArticlePipelineService()

export interface Timed<T> {
  data: T
  ms: number
}

const parse = (raw: unknown) => {
  if (typeof raw !== 'string') return raw
  try {
    return JSON.parse(raw)
  } catch {
    return raw
  }
}

// ── Activity log: every call that goes through the Graft, shown in the dashboard's pink strip ──
export interface GraftCall {
  id: number
  method: string
  ms: number
  ok: boolean
  at: number
}

let callId = 0
let calls: GraftCall[] = []
const listeners = new Set<() => void>()

export const graftActivity = {
  subscribe(fn: () => void) {
    listeners.add(fn)
    return () => { listeners.delete(fn) }
  },
  snapshot: () => calls,
}

function record(method: string, ms: number, ok: boolean) {
  calls = [{ id: ++callId, method, ms, ok, at: Date.now() }, ...calls].slice(0, 40)
  listeners.forEach(fn => fn())
}

/** Calls a Python receiver method through the generated Graft (WebSocket). */
export async function callGraft(method: string, ...args: unknown[]): Promise<Timed<any>> {
  const t0 = performance.now()
  try {
    const raw = await service[method](...args)
    const ms = performance.now() - t0
    record(method, ms, true)
    return { data: parse(raw), ms }
  } catch (err) {
    record(method, performance.now() - t0, false)
    throw err
  }
}

// ── MCP: the Gateway's built-in endpoint (streamable HTTP, JSON-RPC) ───────────
let sessionId: string | null = null
let rpcId = 0

async function mcpRequest(method: string, params?: unknown): Promise<any> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    Accept: 'application/json, text/event-stream',
  }
  if (sessionId) headers['Mcp-Session-Id'] = sessionId
  const res = await fetch(MCP_URL, {
    method: 'POST',
    headers,
    body: JSON.stringify({ jsonrpc: '2.0', id: ++rpcId, method, params }),
  })
  const sid = res.headers.get('Mcp-Session-Id')
  if (sid) sessionId = sid
  const body = await res.json()
  if (body.error) throw new Error(body.error.message ?? 'MCP error')
  return body.result
}

async function mcpSession() {
  if (sessionId) return
  await mcpRequest('initialize', {
    protocolVersion: '2025-03-26',
    capabilities: {},
    clientInfo: { name: 'graft-dashboard', version: '1.0.0' },
  })
  if (!sessionId) {
    throw new Error('MCP session id not readable: check the gateway CORS config exposes Mcp-Session-Id')
  }
}

export async function mcpListTools(): Promise<string[]> {
  await mcpSession()
  const result = await mcpRequest('tools/list')
  return result.tools.map((t: { name: string }) => t.name)
}

/** Calls the same Python method as an MCP tool (snake_case name). */
export async function callMcp(tool: string, args: Record<string, unknown> = {}): Promise<Timed<any>> {
  await mcpSession()
  const t0 = performance.now()
  const result = await mcpRequest('tools/call', { name: tool, arguments: args })
  const ms = performance.now() - t0
  if (result.isError) throw new Error(result.content?.[0]?.text ?? 'MCP tool error')
  return { data: parse(result.structuredContent?.value), ms }
}

export const median = (xs: number[]) => {
  const s = [...xs].sort((a, b) => a - b)
  const m = Math.floor(s.length / 2)
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2
}
