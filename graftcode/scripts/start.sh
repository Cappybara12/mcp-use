#!/bin/bash
# One-command launcher.
#   bash scripts/start.sh           gateway + install graft + test + dashboard
#   bash scripts/start.sh --no-ui   gateway + install graft + test only
# Stop everything with: bash scripts/stop.sh
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG="$ROOT/logs/gateway.log"
WITH_UI=1; [ "${1:-}" = "--no-ui" ] && WITH_UI=0
mkdir -p "$ROOT/logs"

# Callers follow the gateway's ports, so GRAFT_PORT / GRAFT_VISION_PORT move everything together.
export GRAFT_HOST="${GRAFT_HOST:-ws://localhost:${GRAFT_PORT:-8080}/ws}"
export VITE_GRAFT_HOST="${VITE_GRAFT_HOST:-$GRAFT_HOST}"
export VITE_GRAFT_MCP_URL="${VITE_GRAFT_MCP_URL:-http://localhost:${GRAFT_VISION_PORT:-8081}/mcp}"

need() { command -v "$1" >/dev/null 2>&1 || { echo "Missing prerequisite: $1 ($2)"; exit 1; }; }
need python3 "https://www.python.org/downloads/"
need node "https://nodejs.org/"
need npm "https://nodejs.org/"

bash "$ROOT/scripts/stop.sh" >/dev/null 2>&1

# Optional Superlinked SIE (semantic search, topic relevance, related reads).
# An explicit SIE_URL wins; otherwise a local sie-server is started if one is installed.
# Skip it with SIE=off. Without SIE every feature falls back to keyword matching.
if [ -z "${SIE_URL:-}" ] && [ "${SIE:-auto}" != "off" ]; then
  SIE_PORT="${SIE_PORT:-8090}"
  SIE_BIN="${SIE_BIN:-}"
  [ -z "$SIE_BIN" ] && [ -x "$HOME/.sie-venv/bin/sie-server" ] && SIE_BIN="$HOME/.sie-venv/bin/sie-server"
  [ -z "$SIE_BIN" ] && SIE_BIN="$(command -v sie-server || true)"
  if curl -s "http://localhost:$SIE_PORT/readyz" 2>/dev/null | grep -qi ok; then
    echo "==> Using the Superlinked SIE server already running on port $SIE_PORT"
    export SIE_URL="http://localhost:$SIE_PORT"
  elif [ -n "$SIE_BIN" ]; then
    echo "==> Starting Superlinked SIE on port $SIE_PORT (log: $ROOT/logs/sie.log)"
    set -m
    nohup "$SIE_BIN" serve --port "$SIE_PORT" > "$ROOT/logs/sie.log" 2>&1 &
    echo $! > "$ROOT/logs/sie.pid"
    set +m
    for i in $(seq 1 90); do
      curl -s "http://localhost:$SIE_PORT/readyz" 2>/dev/null | grep -qi ok && break
      sleep 1
    done
    if curl -s "http://localhost:$SIE_PORT/readyz" 2>/dev/null | grep -qi ok; then
      export SIE_URL="http://localhost:$SIE_PORT"
    else
      echo "!! SIE did not start (see logs/sie.log); continuing with keyword matching"
    fi
  else
    echo "==> Superlinked SIE not installed; using keyword matching (see README: semantic search)"
  fi
fi

echo "==> Starting Graftcode gateway (log: $LOG)"
set -m
nohup bash "$ROOT/scripts/run_gateway.sh" > "$LOG" 2>&1 &
echo $! > "$ROOT/logs/gateway.pid"
set +m

echo "==> Waiting for gateway..."
for i in $(seq 1 90); do
  grep -q "Websocket server is available" "$LOG" 2>/dev/null && break
  # fail fast if the gateway process already exited
  kill -0 "$(cat "$ROOT/logs/gateway.pid")" 2>/dev/null || break
  sleep 1
done
if ! grep -q "Websocket server is available" "$LOG"; then
  echo "Gateway did not start. Last log lines:"; tail -30 "$LOG"; exit 1
fi

# The registry ID changes on every restart, so read the install command from the log.
INSTALL_CMD="$(grep -m1 '^npm install --registry' "$LOG")"
[ -z "$INSTALL_CMD" ] && { echo "Could not find the npm install command in $LOG"; tail -30 "$LOG"; exit 1; }
PKG="$(printf '%s' "$INSTALL_CMD" | grep -oE '@graft/[^@ ]+' | head -1)"
echo "==> Graft package: $PKG"

for dir in test-client ui; do
  echo "==> Installing graft in $dir"
  (cd "$ROOT/$dir" && npm install --no-audit --no-fund >/dev/null 2>&1; eval "$INSTALL_CMD --no-save --no-audit --no-fund") \
    || { echo "Install failed in $dir"; exit 1; }
  # Callers read the generated package name from this file (it can differ per machine).
  printf '{ "name": "%s" }\n' "$PKG" > "$ROOT/$dir/graft-package.json"
done

echo "==> Running Node -> Python test"
(cd "$ROOT/test-client" && node test.js) || echo "!! test.js reported a failure (see above)"

if [ "$WITH_UI" = "1" ]; then
  echo "==> Starting dashboard"
  set -m
  (cd "$ROOT/ui" && nohup ./node_modules/.bin/vite > "$ROOT/logs/ui.log" 2>&1 & echo $! > "$ROOT/logs/ui.pid")
  set +m
  sleep 4
  # Vite moves to the next free port when 5173 is taken, so report the one it chose.
  UI_URL="$(grep -oE 'http://localhost:[0-9]+' "$ROOT/logs/ui.log" | head -1)"
  echo "Dashboard:      ${UI_URL:-http://localhost:5173}"
fi
if [ -n "${SIE_URL:-}" ]; then
  # Warm the MCP side too, so the first suggestion in a demo is not the slow one.
  GRAFT_VISION_PORT="${GRAFT_VISION_PORT:-8081}" bash "$ROOT/scripts/mcp-check.sh" suggest_next_article >/dev/null 2>&1 &
  echo "Superlinked SIE: $SIE_URL"
fi
echo "Graft Vision:   http://localhost:${GRAFT_VISION_PORT:-8081}"
echo "Logs:           $ROOT/logs/"
echo "Stop all:       bash scripts/stop.sh"
