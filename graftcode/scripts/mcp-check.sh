#!/bin/bash
# Verifies the Gateway's built-in MCP endpoint: lists the tools and calls one.
# Usage: bash scripts/mcp-check.sh [tool_name] [json_arguments]
#   e.g.  bash scripts/mcp-check.sh get_topic_sources '{"topic":"goa"}'   (default tool: suggest_next_article)
URL="http://localhost:${GRAFT_VISION_PORT:-8081}/mcp"
TOOL="${1:-suggest_next_article}"
ARGS="${2:-}"
[ -z "$ARGS" ] && ARGS='{}'
H=(-H "Content-Type: application/json" -H "Accept: application/json, text/event-stream")

SID="$(curl -s -D - -o /dev/null -X POST "$URL" "${H[@]}" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"mcp-check","version":"1"}}}' \
  | awk -F': ' 'tolower($1)=="mcp-session-id"{print $2}' | tr -d '\r')"
[ -z "$SID" ] && { echo "Could not open an MCP session at $URL (is the gateway running?)"; exit 1; }

echo "Tools at $URL:"
curl -s -X POST "$URL" "${H[@]}" -H "Mcp-Session-Id: $SID" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \
  | python3 -c "import sys,json;[print('  -',t['name']) for t in json.load(sys.stdin)['result']['tools']]"
echo; echo "Calling $TOOL:"
curl -s -X POST "$URL" "${H[@]}" -H "Mcp-Session-Id: $SID" \
  -d "{\"jsonrpc\":\"2.0\",\"id\":3,\"method\":\"tools/call\",\"params\":{\"name\":\"$TOOL\",\"arguments\":$ARGS}}" \
  | python3 -c "import sys,json;d=json.load(sys.stdin);print(d['result']['structuredContent']['value'] if 'result' in d else d)"
