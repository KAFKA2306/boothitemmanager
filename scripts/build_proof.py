#!/usr/bin/env python3
"""Generate truthful deployment metadata from the API artefacts being published."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SHARD_RE = re.compile(r"catalog_summary_part(\d+)\.json$")


def _read_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else {}


def build_proof(api_dir: Path, *, built_at: datetime | None = None) -> dict[str, Any]:
    shards = sorted(
        api_dir.glob("catalog_summary_part*.json"),
        key=lambda path: int(SHARD_RE.search(path.name).group(1))
        if SHARD_RE.search(path.name)
        else 10**9,
    )
    if not shards:
        raise ValueError("catalog has no summary shards")

    item_count = 0
    for path in shards:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError(f"{path} must contain a JSON array")
        item_count += len(payload)

    metadata = _read_object(api_dir / "metadata.json")
    freshness = _read_object(api_dir / "freshness.json")
    timestamp = built_at or datetime.now(timezone.utc)

    return {
        "schema_version": 1,
        "items": item_count,
        "catalog_shards": len(shards),
        "built_at": timestamp.astimezone(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "catalog_updated_at": metadata.get("updated_at"),
        "last_catalog_change_at": freshness.get("last_catalog_change_at"),
        "source": freshness.get("source", "https://booth.pm"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-dir", type=Path, default=Path("api"))
    parser.add_argument("--output", type=Path, default=Path("dist/proof.json"))
    args = parser.parse_args()
    proof = build_proof(args.api_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(proof, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(proof, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
