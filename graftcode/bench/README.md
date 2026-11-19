# Benchmark: Graftcode Gateway 1.4.10 → 1.5.0 (Stable)

This project moved from Graftcode Gateway **1.4.10** (Alpha) to **1.5.0** (Stable) with no code
changes: same receiver, same generated Graft, same MCP endpoint. After the switch, the Node
end-to-end test, the dashboard and the MCP tools ran unchanged on 1.5.0. This folder measures
what changed.

## Results (clean rounds)

Apple M5, 16 GB, macOS 26.4. Three rounds, each running 1.4.10 then 1.5.0 back to back. The
numbers are medians; the last column counts how many of the three rounds 1.5.0 won.

| Metric | 1.4.10 | 1.5.0 | Change | 1.5.0 better in |
|---|---|---|---|---|
| Typed call (Node → Python over WebSocket), p50 | 0.222 ms | 0.194 ms | **−12.6%** | 3/3 |
| Typed call, p99 | 0.391 ms | 0.347 ms | −11.3% | 3/3 |
| Heavier call (`list_drafts`), p50 | 0.213 ms | 0.189 ms | −11.3% | 3/3 |
| Throughput, 16 concurrent callers | 5,218 calls/s | 5,952 calls/s | **+14.1%** | 3/3 |
| Latency under that load, p95 | 3.38 ms | 3.08 ms | −9.1% | 3/3 |
| MCP `tools/call`, p50 | 2.11 ms | 2.12 ms | no change | 1/3 |
| Memory (RSS, after load) | 93 MB | 98 MB | +6% | |
| Startup to ready | 5.9 s | 5.8 s | no change | |

Full per-round output: [`RESULTS.md`](RESULTS.md) and `results/<version>/run<N>/`.

### Native async

Stable adds native async. A Python receiver can expose `async def` methods and the Node Graft
awaits them. In this test both versions accepted `async def` and returned the right values.

Concurrency did **not** change. 20 parallel calls of a 200 ms wait over one connection took
about 4.05 s on both versions, written as `def` or as `async def`: calls on one connection run one
at a time. Spread over 5 connections, the same 20 calls took about 1.0 s on both. So in this
setup async in Stable gives you a cleaner API rather than more throughput. Use more connections
or processes for parallel slow calls.

## Caveats

- **These are local round trips** on one machine (client and gateway on localhost), with a light
  method. They show gateway overhead, not network latency.
- **Rounds 1–3 ran while the machine was busy** (load average about 21). Startup took up to 65 s,
  and latency varied widely for both versions. Over all six rounds, 1.5.0 still won 5 of 6 on
  typed-call latency and throughput: −15.9% p50 and +13.4% calls/s. The headline uses rounds 4–6,
  when load was normal.
- **Three clean rounds is a small sample**, although 1.5.0 won every one on typed calls.

## Method

- **Receiver:** this repo's `ArticlePipelineService` in demo mode (bundled sample data, no SIE,
  no API keys), started with `scripts/run_gateway.sh` on ports 9180/9181.
- **Client:** the generated Graft installed from the gateway's registry, in Node 24.
- **Per run:**
  - Typed calls: 2,000 sequential `getPipelineStatus` calls after 100 warm-up calls.
  - Heavier calls: 500 `listDrafts`.
  - Load: 16 concurrent callers for 10 s.
  - MCP: 500 `tools/call` requests to `/mcp`.
  - Memory: RSS of the gateway process.
  - Startup: launch until "Websocket server is available".
- **Async probe:** `probe/async_probe/probe.py`, the same 200 ms wait as `def` and `async def`.

## Reproduce

```bash
bash bench/run.sh v1.4.10 path/to/gg-1.4.10 3
bash bench/run.sh v1.5.0  path/to/gg-1.5.0  3
python3 bench/summarize.py v1.4.10 v1.5.0
```

`BENCH_N`, `BENCH_CONCURRENCY` and `BENCH_SECONDS` change the workload, and `BENCH_START`
numbers the runs.
