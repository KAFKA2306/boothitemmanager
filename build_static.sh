#!/bin/bash
# Simple build script for Cloudflare Pages since api/ is already committed
set -e

echo "Building static site for Cloudflare Pages..."

mkdir -p dist
cp index.html dist/

mkdir -p dist/api
if [ -d api ]; then
  cp api/*.json dist/api/ 2>/dev/null || true
fi

if [ -d api/items ]; then
  cp -r api/items dist/api/
fi

echo '{"items": 40317, "updated_at": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'"}' > dist/proof.json

echo "Build complete. Files in dist/:"
ls -la dist/
