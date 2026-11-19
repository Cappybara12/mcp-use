// Measures one running Graftcode Gateway: typed-client (WebSocket) latency and throughput,
// MCP latency, and a heavier call. Usage (bench/run.sh calls this):
//   node bench.js <graft-package-name> <ws-url> <mcp-url> <out.json>
const fs = require("fs");
const path = require("path");

const [pkg, wsUrl, mcpUrl, outFile] = process.argv.slice(2);
const N = Number(process.env.BENCH_N || 2000);           // sequential calls per test
const CONC = Number(process.env.BENCH_CONCURRENCY || 16); // parallel callers
const SECONDS = Number(process.env.BENCH_SECONDS || 10);  // throughput window

const { ArticlePipelineService, GraftConfig } = require(require.resolve(pkg, { paths: [process.cwd()] }));
GraftConfig.host = wsUrl;
const svc = new ArticlePipelineService();

const now = () => Number(process.hrtime.bigint()) / 1e6;
function stats(ms) {
  const s = [...ms].sort((a, b) => a - b);
  const q = (p) => s[Math.min(s.length - 1, Math.floor(p * s.length))];
  return {
    n: s.length,
    p50_ms: +q(0.5).toFixed(3),
    p95_ms: +q(0.95).toFixed(3),
    p99_ms: +q(0.99).toFixed(3),
    mean_ms: +(s.reduce((a, b) => a + b, 0) / s.length).toFixed(3),
  };
}

async function sequential(fn, n) {
  for (let i = 0; i < Math.min(100, n); i++) await fn(); // warm-up
  const out = [];
  for (let i = 0; i < n; i++) {
    const t = now();
    await fn();
    out.push(now() - t);
  }
  return stats(out);
}

async function throughput(fn, conc, seconds) {
  const end = now() + seconds * 1000;
  let calls = 0, errors = 0;
  const lat = [];
  await Promise.all(Array.from({ length: conc }, async () => {
    while (now() < end) {
      const t = now();
      try { await fn(); calls++; lat.push(now() - t); } catch { errors++; }
    }
  }));
  return { concurrency: conc, seconds, calls, errors, calls_per_sec: +(calls / seconds).toFixed(1), ...stats(lat) };
}

let sid = null, rpcId = 0;
async function mcp(method, params) {
  const headers = { "Content-Type": "application/json", Accept: "application/json, text/event-stream" };
  if (sid) headers["Mcp-Session-Id"] = sid;
  const res = await fetch(mcpUrl, { method: "POST", headers, body: JSON.stringify({ jsonrpc: "2.0", id: ++rpcId, method, params }) });
  sid = res.headers.get("mcp-session-id") || sid;
  const body = await res.json();
  if (body.error) throw new Error(body.error.message);
  return body.result;
}

(async () => {
  const result = { pkg, started: new Date().toISOString(), N, CONC, SECONDS };
  result.graft_status_sequential = await sequential(() => svc.getPipelineStatus(), N);
  result.graft_list_drafts_sequential = await sequential(() => svc.listDrafts(), Math.round(N / 4));
  result.graft_status_throughput = await throughput(() => svc.getPipelineStatus(), CONC, SECONDS);
  await mcp("initialize", { protocolVersion: "2025-03-26", capabilities: {}, clientInfo: { name: "bench", version: "1" } });
  const tools = await mcp("tools/list");
  result.mcp_tools = tools.tools.length;
  result.mcp_status_sequential = await sequential(
    () => mcp("tools/call", { name: "get_pipeline_status", arguments: {} }), Math.round(N / 4));
  fs.writeFileSync(outFile, JSON.stringify(result, null, 2));
  console.log(JSON.stringify(result));
  process.exit(0);
})().catch((e) => { console.error(e); process.exit(1); });
