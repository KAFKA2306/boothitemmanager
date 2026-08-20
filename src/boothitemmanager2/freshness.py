from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

UTC = timezone.utc


def utc_now() -> datetime:
    return datetime.now(UTC)


def isoformat_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def atomic_write_json(path: Path, payload: Any, *, compact: bool = False) -> None:
    if compact:
        text = json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"
    else:
        text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    atomic_write_text(path, text)


def stable_refresh_batch(
    item_ids: Iterable[str],
    *,
    now: datetime,
    batch_size: int,
    interval_minutes: int = 15,
) -> list[str]:
    """Return a deterministic bounded slice for the current refresh slot.

    The sorted order is based on SHA-256 rather than item id so adjacent BOOTH ids are
    spread across runs. No mutable cursor is required, which makes scheduled runs safe
    on ephemeral GitHub-hosted runners.
    """

    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    if interval_minutes <= 0:
        raise ValueError("interval_minutes must be positive")

    ids = sorted({str(item_id) for item_id in item_ids}, key=sha256_text)
    if not ids:
        return []

    bucket_count = (len(ids) + batch_size - 1) // batch_size
    slot_seconds = interval_minutes * 60
    slot = int(now.astimezone(UTC).timestamp() // slot_seconds) % bucket_count
    start = slot * batch_size
    return ids[start : start + batch_size]


def refresh_cycle_hours(item_count: int, batch_size: int, interval_minutes: int = 15) -> float:
    if item_count <= 0:
        return 0.0
    buckets = (item_count + batch_size - 1) // batch_size
    return round(buckets * interval_minutes / 60.0, 2)
