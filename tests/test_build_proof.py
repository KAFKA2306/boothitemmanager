from datetime import datetime, timezone
from pathlib import Path
import importlib.util
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('build_proof', ROOT / 'scripts' / 'build_proof.py')
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


def test_build_proof_counts_actual_records_and_separates_build_time(tmp_path: Path):
    api = tmp_path / 'api'
    api.mkdir()
    (api / 'catalog_summary_part1.json').write_text(json.dumps([{'id': '1'}, {'id': '2'}]), encoding='utf-8')
    (api / 'catalog_summary_part2.json').write_text(json.dumps([{'id': '3'}]), encoding='utf-8')
    (api / 'metadata.json').write_text(json.dumps({'updated_at': '2026-08-20T00:00:00Z'}), encoding='utf-8')
    (api / 'freshness.json').write_text(json.dumps({'last_catalog_change_at': '2026-08-20T01:00:00Z', 'source': 'https://booth.pm'}), encoding='utf-8')

    proof = MOD.build_proof(api, built_at=datetime(2026, 8, 21, tzinfo=timezone.utc))
    assert proof['items'] == 3
    assert proof['catalog_shards'] == 2
    assert proof['built_at'] == '2026-08-21T00:00:00Z'
    assert proof['catalog_updated_at'] == '2026-08-20T00:00:00Z'
    assert proof['last_catalog_change_at'] == '2026-08-20T01:00:00Z'
