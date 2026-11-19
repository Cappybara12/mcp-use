# Graftcode Gateway v1.4.10 vs v1.5.0

3 paired rounds (rounds 4, 5, 6), each running v1.4.10 then v1.5.0 back to back on the same machine. Medians across rounds; "wins" counts rounds where v1.5.0 was better.

Machine: Apple M5 / 16 GB, macOS 26.4, Node v24.18.0, Python 3.12. Receiver: this repo's ArticlePipelineService in demo mode (bundled sample data, no SIE, no API keys).

| Metric | v1.4.10 | v1.5.0 | Change | v1.5.0 wins |
|---|---|---|---|---|
| Typed call, sequential: p50 (ms) | 0.222 | 0.194 | -12.6% | 3/3 |
| Typed call, sequential: p99 (ms) | 0.391 | 0.347 | -11.3% | 3/3 |
| Heavier call (list_drafts): p50 (ms) | 0.213 | 0.189 | -11.3% | 3/3 |
| Throughput, 16 callers (calls/s) | 5217.700 | 5952.400 | +14.1% | 3/3 |
| Latency under load: p95 (ms) | 3.382 | 3.075 | -9.1% | 3/3 |
| MCP tools/call: p50 (ms) | 2.113 | 2.115 | +0.1% | 1/3 |
| Idle memory, RSS (MB) | 93.6 | 98.2 | +4.9% | |
| Memory after load, RSS (MB) | 93.0 | 98.5 | +5.9% | |
| Startup to ready (s) | 5.9 | 5.8 | -1.8% | |

## Async probe

20 parallel calls of a method that waits 200 ms, written as `def` (time.sleep) and as `async def` (asyncio.sleep), through one Graft client. Fully parallel would take ~200 ms; one at a time ~4,000 ms.

| Round | Version | sync wall (ms) | async wall (ms) | async, 5 connections (ms) | async values correct |
|---|---|---|---|---|---|
| 4 | v1.4.10 | 4102 | 4053 | 1007.5 | True |
| 4 | v1.5.0 | 4098 | 4051 | 1007.5 | True |
| 5 | v1.4.10 | 4108 | 4054 | 1009.1 | True |
| 5 | v1.5.0 | 4094 | 4048 | 1060.7 | True |
| 6 | v1.4.10 | 4103 | 4058 | 1015.3 | True |
| 6 | v1.5.0 | 4100 | 4052 | 1018.8 | True |
