"""Summarize bench/results/<version>/run<N>/ into bench/RESULTS.md (paired by round).

    python3 bench/summarize.py v1.4.10 v1.5.0
"""
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OLD, NEW = sys.argv[1], sys.argv[2]
MIN_ROUND = int(sys.argv[3]) if len(sys.argv) > 3 else 1

METRICS = [
    ("Typed call, sequential: p50 (ms)", "graft_status_sequential", "p50_ms", "lower"),
    ("Typed call, sequential: p99 (ms)", "graft_status_sequential", "p99_ms", "lower"),
    ("Heavier call (list_drafts): p50 (ms)", "graft_list_drafts_sequential", "p50_ms", "lower"),
    ("Throughput, 16 callers (calls/s)", "graft_status_throughput", "calls_per_sec", "higher"),
    ("Latency under load: p95 (ms)", "graft_status_throughput", "p95_ms", "lower"),
    ("MCP tools/call: p50 (ms)", "mcp_status_sequential", "p50_ms", "lower"),
]


def load(version, rnd):
    d = ROOT / "results" / version / f"run{rnd}"
    try:
        return {
            "bench": json.loads((d / "bench.json").read_text()),
            "meta": json.loads((d / "meta.json").read_text()),
            "async": json.loads((d / "async.json").read_text()) if (d / "async.json").exists() else None,
        }
    except FileNotFoundError:
        return None


rounds = []
for rnd in range(MIN_ROUND, 100):
    a, b = load(OLD, rnd), load(NEW, rnd)
    if a is None and b is None:
        if rnd > MIN_ROUND + 20:
            break
        continue
    if a and b:
        rounds.append((rnd, a, b))

lines = [f"# Graftcode Gateway {OLD} vs {NEW}", ""]
lines.append(f"{len(rounds)} paired rounds (rounds {', '.join(str(r) for r, _, _ in rounds)}), each running {OLD} then {NEW} "
             "back to back on the same machine. Medians across rounds; \"wins\" counts rounds where "
             f"{NEW} was better.")
lines.append("")
m = rounds[0][1]["meta"]
lines.append(f"Machine: {m['machine']}, macOS {m['os']}, Node {m['node']}, Python {m['python']}. "
             "Receiver: this repo's ArticlePipelineService in demo mode (bundled sample data, no SIE, no API keys).")
lines.append("")
lines.append(f"| Metric | {OLD} | {NEW} | Change | {NEW} wins |")
lines.append("|---|---|---|---|---|")
for label, key, field, better in METRICS:
    olds = [a["bench"][key][field] for _, a, _ in rounds]
    news = [b["bench"][key][field] for _, _, b in rounds]
    o, n = statistics.median(olds), statistics.median(news)
    change = (n - o) / o * 100 if o else 0
    wins = sum((y < x) if better == "lower" else (y > x) for x, y in zip(olds, news))
    lines.append(f"| {label} | {o:.3f} | {n:.3f} | {change:+.1f}% | {wins}/{len(rounds)} |")
for label, key in (("Idle memory, RSS (MB)", "rss_idle_kb"), ("Memory after load, RSS (MB)", "rss_after_load_kb"),
                   ("Startup to ready (s)", "startup_to_ready_ms")):
    div = 1024 if "kb" in key else 1000
    o = statistics.median(a["meta"][key] for _, a, _ in rounds) / div
    n = statistics.median(b["meta"][key] for _, _, b in rounds) / div
    lines.append(f"| {label} | {o:.1f} | {n:.1f} | {(n - o) / o * 100:+.1f}% | |")

lines += ["", "## Async probe", "",
          "20 parallel calls of a method that waits 200 ms, written as `def` (time.sleep) and as `async def` "
          "(asyncio.sleep), through one Graft client. Fully parallel would take ~200 ms; one at a time ~4,000 ms.", "",
          "| Round | Version | sync wall (ms) | async wall (ms) | async, 5 connections (ms) | async values correct |",
          "|---|---|---|---|---|---|"]
for rnd, a, b in rounds:
    for v, r in ((OLD, a), (NEW, b)):
        p = r["async"]
        if not p:
            continue
        multi = p.get("async_multi_connection", {}).get("wall_ms", "")
        correct = p["async"].get("returned_expected_value", "")
        lines.append(f"| {rnd} | {v} | {p['sync']['wall_ms']:.0f} | {p['async']['wall_ms']:.0f} | {multi} | {correct} |")

out = ROOT / "RESULTS.md"
out.write_text("\n".join(lines) + "\n")
print("\n".join(lines))
