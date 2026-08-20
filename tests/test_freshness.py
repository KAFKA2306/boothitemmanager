from datetime import datetime, timezone
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from boothitemmanager2.freshness import atomic_write_json, refresh_cycle_hours, stable_refresh_batch


def test_stable_refresh_batch_is_bounded_and_deterministic():
    ids = [str(i) for i in range(1, 1001)]
    now = datetime(2026, 8, 21, 0, 7, tzinfo=timezone.utc)
    first = stable_refresh_batch(ids, now=now, batch_size=120, interval_minutes=15)
    second = stable_refresh_batch(reversed(ids), now=now, batch_size=120, interval_minutes=15)
    assert first == second
    assert 0 < len(first) <= 120
    assert len(first) == len(set(first))


def test_stable_refresh_batch_rotates_between_slots():
    ids = [str(i) for i in range(1, 1001)]
    a = stable_refresh_batch(ids, now=datetime(2026, 8, 21, 0, 7, tzinfo=timezone.utc), batch_size=120)
    b = stable_refresh_batch(ids, now=datetime(2026, 8, 21, 0, 22, tzinfo=timezone.utc), batch_size=120)
    assert a != b
    assert set(a).isdisjoint(set(b))


def test_refresh_cycle_hours_matches_bounded_rotation():
    assert refresh_cycle_hours(40317, 120, 15) == 84.0


def test_atomic_write_json_replaces_complete_file(tmp_path: Path):
    target = tmp_path / 'state.json'
    atomic_write_json(target, {'value': 1})
    atomic_write_json(target, {'value': 2})
    assert json.loads(target.read_text(encoding='utf-8')) == {'value': 2}
    assert not list(tmp_path.glob('.state.json.tmp-*'))
