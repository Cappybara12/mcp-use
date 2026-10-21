#!/bin/bash
# Stops the gateway and dashboard started by scripts/start.sh.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MY_PGID="$(ps -o pgid= -p $$ | tr -d ' ')"

for name in gateway ui; do
  pidfile="$ROOT/logs/$name.pid"
  [ -f "$pidfile" ] || continue
  pid="$(cat "$pidfile")"
  if kill -0 "$pid" 2>/dev/null; then
    pgid="$(ps -o pgid= -p "$pid" | tr -d ' ')"
    # Kill the whole group only when the process leads its own group and it
    # is not the group this script (or start.sh) is running in.
    if [ "$pgid" = "$pid" ] && [ "$pgid" != "$MY_PGID" ]; then
      kill -- -"$pid" 2>/dev/null
    else
      kill "$pid" 2>/dev/null
    fi
    echo "stopped $name"
  fi
  rm -f "$pidfile"
done

# Safety net: stop a dev server still listening on the dashboard port, but only
# if it was started from this project's ui/ folder.
UI_PORT="${GRAFT_UI_PORT:-5173}"
for pid in $(lsof -t -iTCP:"$UI_PORT" -iTCP:5174 -sTCP:LISTEN 2>/dev/null); do
  cwd="$(lsof -a -p "$pid" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p')"
  if [ "$cwd" = "$ROOT/ui" ]; then
    kill "$pid" 2>/dev/null && echo "stopped stray dashboard (pid $pid)"
  fi
done
