#!/bin/bash
# Benchmarks one Graftcode Gateway binary against this repo's receiver (demo mode, sample data,
# no SIE, no API keys) and the async probe. Results go to bench/results/<label>/run<N>/.
#   bash bench/run.sh <label> <path-to-gg> [runs]
#   e.g. bash bench/run.sh v1.4.10 usr/local/bin/gg 3
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LABEL="$1"; GG="$(cd "$(dirname "$2")" && pwd)/$(basename "$2")"; RUNS="${3:-3}"
PORT=9180; VPORT=9181; PPORT=9182; PVPORT=9183
CLIENT="$ROOT/bench/.clients/$LABEL"
PY="/Library/Frameworks/Python.framework/Versions/3.12"
mkdir -p "$CLIENT"
[ -f "$CLIENT/package.json" ] || (cd "$CLIENT" && npm init -y >/dev/null)

ms() { python3 -c 'import time; print(int(time.time()*1000))'; }
rss_kb() {  # resident memory of a process and its children
  local total=0
  for p in "$1" $(pgrep -P "$1" 2>/dev/null); do
    total=$((total + $(ps -o rss= -p "$p" 2>/dev/null | tr -d ' ' || echo 0)))
  done
  echo "$total"
}
wait_ready() {  # wait_ready <log> <pid>  -> prints ms waited, or -1
  local t0; t0=$(ms)
  for _ in $(seq 1 1200); do
    grep -q "Websocket server is available" "$1" 2>/dev/null && { echo $(( $(ms) - t0 )); return; }
    kill -0 "$2" 2>/dev/null || { echo -1; return; }
    sleep 0.05
  done
  echo -1
}
install_graft() {  # install_graft <log>  -> prints package name
  local cmd pkg
  cmd="$(grep -m1 '^npm install --registry' "$1")"
  pkg="$(printf '%s' "$cmd" | grep -oE '@graft/[^@ ]+' | head -1)"
  (cd "$CLIENT" && eval "$cmd --no-save --no-audit --no-fund" >/dev/null 2>&1)
  echo "$pkg"
}
stop() { kill "$1" 2>/dev/null; for _ in $(seq 1 40); do kill -0 "$1" 2>/dev/null || return; sleep 0.1; done; kill -9 "$1" 2>/dev/null; }

START="${BENCH_START:-1}"
for RUN in $(seq "$START" $((START + RUNS - 1))); do
  OUT="$ROOT/bench/results/$LABEL/run$RUN"; mkdir -p "$OUT"
  echo "== $LABEL run $RUN"

  # 1. The real receiver (ArticlePipelineService), demo mode.
  T0=$(ms)
  ( exec env -u SIE_URL GG_BIN="$GG" GRAFT_PORT=$PORT GRAFT_VISION_PORT=$VPORT \
      WAYZYY_WRITER_DIR=/nonexistent WAYZYY_SCANNER_DIR=/nonexistent \
      SIE_CACHE_FILE="$OUT/sie-unused.json" \
      bash "$ROOT/scripts/run_gateway.sh" ) > "$OUT/gateway.log" 2>&1 &
  GPID=$!
  READY=$(wait_ready "$OUT/gateway.log" $GPID)
  [ "$READY" = "-1" ] && { echo "gateway failed to start"; tail -20 "$OUT/gateway.log"; stop $GPID; exit 1; }
  READY=$(( $(ms) - T0 ))
  VERSION="$(grep -oE 'Gateway version [0-9.]+' "$OUT/gateway.log" | head -1 | awk '{print $3}')"
  PKG="$(install_graft "$OUT/gateway.log")"
  sleep 2
  RSS_IDLE=$(rss_kb $GPID)
  (cd "$CLIENT" && node "$ROOT/bench/bench.js" "$PKG" "ws://localhost:$PORT/ws" "http://localhost:$VPORT/mcp" "$OUT/bench.json") > "$OUT/bench.out" 2>&1 \
    || { echo "bench failed:"; tail -5 "$OUT/bench.out"; }
  RSS_LOAD=$(rss_kb $GPID)
  stop $GPID

  # 2. The async probe (same 200 ms wait, sync vs async).
  CA=/opt/homebrew/etc/openssl@3/cert.pem  # same CA bundle scripts/run_gateway.sh uses
  ( cd "$ROOT/bench/probe" && [ -f "$CA" ] && export SSL_CERT_FILE="$CA" CURL_CA_BUNDLE="$CA"
    DYLD_LIBRARY_PATH="$PY/lib" PYTHONHOME="$PY" exec "$GG" ./async_probe/probe.py --runtime python --types "*AsyncProbe*" --port $PPORT --httpPort $PVPORT ) > "$OUT/probe-gateway.log" 2>&1 &
  PPID_=$!
  if [ "$(wait_ready "$OUT/probe-gateway.log" $PPID_)" != "-1" ]; then
    PPKG="$(install_graft "$OUT/probe-gateway.log")"
    (cd "$CLIENT" && node "$ROOT/bench/async_probe.js" "$PPKG" "ws://localhost:$PPORT/ws" "$OUT/async.json") > "$OUT/async.out" 2>&1 \
      || { echo "async probe failed:"; tail -5 "$OUT/async.out"; }
  else
    echo "probe gateway failed to start"; tail -5 "$OUT/probe-gateway.log"
  fi
  stop $PPID_

  cat > "$OUT/meta.json" <<JSON
{ "label": "$LABEL", "gateway_version": "$VERSION", "startup_to_ready_ms": $READY,
  "rss_idle_kb": $RSS_IDLE, "rss_after_load_kb": $RSS_LOAD,
  "machine": "$(sysctl -n machdep.cpu.brand_string 2>/dev/null) / $(sysctl -n hw.memsize 2>/dev/null | awk '{print $1/1073741824 " GB"}')",
  "os": "$(sw_vers -productVersion 2>/dev/null)", "node": "$(node --version)", "python": "3.12" }
JSON
  echo "   version $VERSION, ready in ${READY} ms, RSS idle $((RSS_IDLE/1024)) MB, after load $((RSS_LOAD/1024)) MB"
done
