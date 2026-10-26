#!/bin/bash
# Save an API key for a Studio workspace using hidden input (nothing is echoed or stored in shell history).
#   bash scripts/add-key.sh WORKSPACE PROVIDER [--default]
# Example:  bash scripts/add-key.sh demo-blog openai --default
set -e
if [ $# -lt 2 ]; then
  echo "Usage: bash scripts/add-key.sh WORKSPACE PROVIDER [--default]"
  echo "Providers: openai anthropic groq moonshot openrouter tinyfish dataforseo github"
  exit 1
fi
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WS="$1"; PROVIDER="$2"; shift 2
cd "$ROOT/receiver"
exec python3 -m article_receiver.studio.cli set-key --workspace "$WS" --provider "$PROVIDER" "$@"
