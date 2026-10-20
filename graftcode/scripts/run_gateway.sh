#!/bin/bash
set -e

export DYLD_LIBRARY_PATH="/Library/Frameworks/Python.framework/Versions/3.12/lib:$DYLD_LIBRARY_PATH"
export PYTHONHOME="/Library/Frameworks/Python.framework/Versions/3.12"
export SSL_CERT_FILE=/opt/homebrew/etc/openssl@3/cert.pem
export CURL_CA_BUNDLE=/opt/homebrew/etc/openssl@3/cert.pem

cd /Users/akshay/graft/receiver

echo "Starting Graftcode Gateway hosting ArticlePipelineService..."
exec /Users/akshay/graft/usr/local/bin/gg ./article_receiver/service.py \
  --runtime python \
  --types "*ArticlePipelineService*" \
  --port 8080 \
  --httpPort 8081 \
  --corsAllowedOrigins "*" \
  --gatewayName "wayzyy-content-engine"
