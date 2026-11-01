#!/usr/bin/env bash
# Simple launcher for the local Pipeline Studio.
# Run from anywhere with: bash scripts/start-studio.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Prefer an explicitly configured gateway, then the common local install, then PATH.
if [[ -z "${GG_BIN:-}" ]]; then
  for candidate in \
    "$HOME/.gemini/antigravity-ide/scratch/wayzyy-site/gg" \
    "$ROOT/usr/local/bin/gg"; do
    if [[ -x "$candidate" ]]; then
      GG_BIN="$candidate"
      export GG_BIN
      break
    fi
  done
fi

# When this folder is inside the mcp-use repository, the article-writer pipeline is its parent.
if [[ -z "${WAYZYY_WRITER_DIR:-}" && -d "$ROOT/../agent" ]]; then
  export WAYZYY_WRITER_DIR="$(cd "$ROOT/.." && pwd)"
fi

exec bash "$ROOT/scripts/start.sh" "$@"
