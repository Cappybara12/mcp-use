#!/bin/bash
# Starts the Graftcode Gateway hosting the Python receiver (foreground).
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Locate the gateway binary: $GG_BIN, then the project-local install, then PATH.
GG="${GG_BIN:-}"
[ -z "$GG" ] && [ -x "$ROOT/usr/local/bin/gg" ] && GG="$ROOT/usr/local/bin/gg"
[ -z "$GG" ] && GG="$(command -v gg || true)"
if [ -z "$GG" ]; then
  echo "Graftcode Gateway (gg) not found."
  echo "Install it from https://docs.graftcode.com/quick-start, or set GG_BIN=/path/to/gg"
  exit 1
fi

# Optional: point Graftcode at a specific Python install. Set PY_HOME to your
# Python prefix if the gateway reports "Cannot find Python installed".
if [ -n "${PY_HOME:-}" ] && [ -d "$PY_HOME" ]; then
  export DYLD_LIBRARY_PATH="$PY_HOME/lib:${DYLD_LIBRARY_PATH:-}"
  export PYTHONHOME="$PY_HOME"
elif [ -d /Library/Frameworks/Python.framework/Versions/3.12 ]; then
  export DYLD_LIBRARY_PATH="/Library/Frameworks/Python.framework/Versions/3.12/lib:${DYLD_LIBRARY_PATH:-}"
  export PYTHONHOME="/Library/Frameworks/Python.framework/Versions/3.12"
fi
# Optional CA bundle override (Homebrew OpenSSL path is used if present).
if [ -f /opt/homebrew/etc/openssl@3/cert.pem ]; then
  export SSL_CERT_FILE=/opt/homebrew/etc/openssl@3/cert.pem
  export CURL_CA_BUNDLE=/opt/homebrew/etc/openssl@3/cert.pem
fi

# CORS for the browser dashboard, including the MCP headers the browser must be able to read.
mkdir -p "$ROOT/logs"
CORS_FILE="$ROOT/logs/cors.config"
cat > "$CORS_FILE" <<CORS
allowedOrigins=${GRAFT_CORS:-http://localhost:5173}
allowedMethods=GET,POST,PUT,PATCH,DELETE,OPTIONS
allowedHeaders=content-type,authorization,accept,MCP-Protocol-Version,Mcp-Session-Id
exposedHeaders=Mcp-Session-Id,MCP-Protocol-Version
allowCredentials=false
CORS

# The receiver reads its configuration with PyYAML.
python3 -c "import yaml" 2>/dev/null || { echo "PyYAML is required: pip install -r receiver/requirements.txt"; exit 1; }

# Niche configuration (brand, categories, suggestion keywords, style rules).
# Defaults to the bundled Wayzyy config; point PIPELINE_CONFIG at your own YAML to retarget it.
if [ -z "${PIPELINE_CONFIG:-}" ]; then
  PIPELINE_CONFIG="$ROOT/receiver/config/wayzyy.yaml"
elif [ -f "$PIPELINE_CONFIG" ]; then
  PIPELINE_CONFIG="$(cd "$(dirname "$PIPELINE_CONFIG")" && pwd)/$(basename "$PIPELINE_CONFIG")"
else
  echo "PIPELINE_CONFIG file not found: $PIPELINE_CONFIG"; exit 1
fi
export PIPELINE_CONFIG
echo "Using pipeline config: $PIPELINE_CONFIG"

# Sample data for demo mode: an explicit WAYZYY_SAMPLE_DIR wins, then the config's data_dir,
# then the bundled sample_data.
if [ -z "${WAYZYY_SAMPLE_DIR:-}" ]; then
  if grep -q '^data_dir:' "$PIPELINE_CONFIG"; then
    unset WAYZYY_SAMPLE_DIR
  else
    export WAYZYY_SAMPLE_DIR="$ROOT/receiver/sample_data"
  fi
fi
cd "$ROOT/receiver"
echo "Starting Graftcode Gateway hosting ArticlePipelineService..."
exec "$GG" ./article_receiver/service.py \
  --runtime python \
  --types "*ArticlePipelineService*" \
  --port "${GRAFT_PORT:-8080}" \
  --httpPort "${GRAFT_VISION_PORT:-8081}" \
  --corsAllowedOrigins "${GRAFT_CORS:-http://localhost:5173}" \
  --corsConfig "$CORS_FILE" \
  --gatewayName "wayzyy-content-engine"
