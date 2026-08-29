#!/bin/bash
# Deterministic static build for Cloudflare Pages and the GitHub Pages mirror.
set -euo pipefail

echo "Building static site..."

python scripts/build_static_distribution.py --api-dir api --output-dir api/v1

rm -rf dist
mkdir -p dist/api dist/seller/market-report

python scripts/build_ui.py --source index.html --output dist/index.html
cp ai-tools.html robots.txt sitemap.xml catalog-ux.css catalog-ux.js catalog-evidence.css catalog-evidence.js kafka-signal.css kafka-signal.js dist/
cp seller/market-report/index.html dist/seller/market-report/index.html

# Canonical browser data is JSON only. Missing required data must fail the build.
cp api/metadata.json dist/api/metadata.json
cp api/ai_tool_candidates.json dist/api/ai_tool_candidates.json
cp api/catalog_summary_part*.json dist/api/
cp -r api/details dist/api/
cp -r api/v1 dist/api/

python scripts/build_seller_market_report.py --api-dir api --output dist/api/seller_market_report.json
python scripts/build_proof.py --api-dir api --output dist/proof.json

python - <<'PY'
import json
from pathlib import Path

manifest = json.loads(Path('dist/api/v1/manifest.json').read_text(encoding='utf-8'))
shards = json.loads(Path('dist/api/v1/shards.json').read_text(encoding='utf-8'))
metadata = json.loads(Path('dist/api/metadata.json').read_text(encoding='utf-8'))

if not metadata.get('avatars'):
    raise SystemExit('dist/api/metadata.json has no avatars')
if not shards.get('shards'):
    raise SystemExit('dist/api/v1/shards.json has no shards')
if shards.get('record_count') != manifest.get('record_count'):
    raise SystemExit('v1 manifest/shard record count mismatch')

for shard in shards['shards']:
    path = Path('dist') / shard['path']
    if not path.is_file():
        raise SystemExit(f'missing canonical catalog shard: {path}')
    rows = json.loads(path.read_text(encoding='utf-8'))
    if len(rows) != shard['records']:
        raise SystemExit(f'catalog shard record count mismatch: {path}')

html = Path('dist/index.html').read_text(encoding='utf-8')
for forbidden in (
    'window.BOOTH_METADATA',
    'window.BOOTH_CATALOG_PART1',
    'fallback script',
    'DATABASE OFFLINE (CORS)',
    'src="api/metadata.js"',
    'src="api/catalog_summary_part1.js"',
):
    if forbidden in html:
        raise SystemExit(f'fallback runtime leaked into dist/index.html: {forbidden}')

print(json.dumps({
    'records': manifest['record_count'],
    'shards': manifest['shard_count'],
    'avatars': len(metadata['avatars']),
}, ensure_ascii=False, sort_keys=True))
PY

test -s dist/api/ai_tool_candidates.json
test -s dist/api/seller_market_report.json
test -s dist/seller/market-report/index.html

echo "Build complete. Files in dist/:"
find dist -maxdepth 3 -type f -print | sort
