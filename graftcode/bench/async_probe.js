// Fires CALLS parallel calls of a 200 ms wait, sync vs async, and reports the wall time and the
// values returned. Also repeats the async burst from PROCS separate processes (one connection each)
// to see whether calls serialize per connection or per receiver.
// Usage: node async_probe.js <graft-package-name> <ws-url> <out.json>
//        node async_probe.js --child <graft-package-name> <ws-url> <calls>
const fs = require("fs");
const { fork } = require("child_process");

const child = process.argv[2] === "--child";
const [pkg, wsUrl, third] = process.argv.slice(child ? 3 : 2);
const CALLS = Number(process.env.PROBE_CALLS || 20);
const PROCS = Number(process.env.PROBE_PROCS || 5);
const WAIT = 200;

const { AsyncProbe, GraftConfig } = require(require.resolve(pkg, { paths: [process.cwd()] }));
GraftConfig.host = wsUrl;
const probe = new AsyncProbe();
const now = () => Number(process.hrtime.bigint()) / 1e6;

async function burst(method, calls) {
  await probe[method](1); // warm-up
  const t = now();
  const res = await Promise.allSettled(Array.from({ length: calls }, () => probe[method](WAIT)));
  const ok = res.filter((r) => r.status === "fulfilled").map((r) => r.value);
  const failed = res.filter((r) => r.status === "rejected");
  return {
    calls,
    wait_ms_each: WAIT,
    wall_ms: +(now() - t).toFixed(1),
    ideal_parallel_ms: WAIT,
    fully_serial_ms: WAIT * calls,
    failed: failed.length,
    returned_expected_value: ok.length > 0 && ok.every((v) => Number(v) === WAIT),
    sample_value: ok.length ? String(ok[0]).slice(0, 80) : "",
    error: failed[0] ? String(failed[0].reason).slice(0, 300) : "",
  };
}

if (child) {
  burst("waitAsync", Number(third)).then((r) => { process.send(r); process.exit(0); });
} else {
  (async () => {
    const out = { pkg, sync: await burst("waitSync", CALLS), async: await burst("waitAsync", CALLS) };
    // Same number of async calls, split over PROCS processes (separate connections).
    const per = Math.ceil(CALLS / PROCS);
    const t = now();
    const parts = await Promise.all(Array.from({ length: PROCS }, () => new Promise((resolve) => {
      const c = fork(__filename, ["--child", pkg, wsUrl, String(per)], { cwd: process.cwd() });
      c.on("message", resolve);
    })));
    out.async_multi_connection = {
      processes: PROCS,
      calls: per * PROCS,
      wall_ms: +(now() - t).toFixed(1),
      per_process_wall_ms: parts.map((p) => p.wall_ms),
      failed: parts.reduce((a, p) => a + p.failed, 0),
      fully_serial_ms: WAIT * per * PROCS,
    };
    fs.writeFileSync(third, JSON.stringify(out, null, 2));
    console.log(JSON.stringify(out));
    process.exit(0);
  })().catch((e) => { console.error(e); process.exit(1); });
}
