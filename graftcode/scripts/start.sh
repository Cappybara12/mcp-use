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

need() { command -v "$1" >/dev/null 2>&1 || { echo "Missing prerequisite: $1 ($2)"; exit 1; }; }
need python3 "https://www.python.org/downloads/"
need node "https://nodejs.org/"
need npm "https://nodejs.org/"

bash "$ROOT/scripts/stop.sh" >/dev/null 2>&1

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
  echo "Dashboard:      http://localhost:5173"
fi
echo "Graft Vision:   http://localhost:${GRAFT_VISION_PORT:-8081}"
echo "Logs:           $ROOT/logs/"
echo "Stop all:       bash scripts/stop.sh"
