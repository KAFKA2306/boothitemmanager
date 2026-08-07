#!/bin/bash
# Deterministic static build for Cloudflare Pages.
set -euo pipefail

echo "Building static site for Cloudflare Pages..."

python scripts/build_static_distribution.py --api-dir api --output-dir api/v1

rm -rf dist
mkdir -p dist
cp index.html dist/

mkdir -p dist/api
if [ -d api ]; then
  cp api/*.json api/*.js dist/api/ 2>/dev/null || true
fi

if [ -d api/details ]; then
  cp -r api/details dist/api/
fi

if [ -d api/v1 ]; then
  cp -r api/v1 dist/api/
fi

python - <<'PY'
import json
from pathlib import Path
manifest = json.loads(Path('api/v1/manifest.json').read_text(encoding='utf-8'))
proof = {
    'items': manifest['record_count'],
    'shards': manifest['shard_count'],
    'manifest': 'api/v1/manifest.json',
}
Path('dist/proof.json').write_text(
    json.dumps(proof, ensure_ascii=False, sort_keys=True) + '\n',
    encoding='utf-8',
)
PY

echo "Build complete. Files in dist/:"
find dist -maxdepth 3 -type f -print | sort
