#!/usr/bin/env python3
"""Build a deterministic, machine-readable distribution index for static catalog shards.

The existing catalog_summary_part*.json files remain the backward-compatible payload.
This script adds a small v1 control plane (manifest, shard index, facets, schema profile)
without fetching BOOTH or mutating the source shards.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

SHARD_RE = re.compile(r"catalog_summary_part(\d+)\.json$")
ID_FIELDS = ("id", "item_id", "product_id", "booth_id")
FACET_FIELDS = {
    "category": ("category", "category_name", "normalized_category"),
    "shop": ("shop_name", "seller", "seller_name", "shop"),
    "status": ("status", "availability", "sale_status"),
    "avatar": ("avatar", "avatar_name", "compatible_avatar"),
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        for key in ("items", "products", "records", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                return [row for row in value if isinstance(row, dict)]
    raise ValueError("unsupported shard structure")


def _stable_id(record: dict[str, Any]) -> str | None:
    for field in ID_FIELDS:
        value = record.get(field)
        if isinstance(value, (str, int)) and str(value).strip():
            return f"{field}:{str(value).strip()}"
    return None


def _json_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int) and not isinstance(value, bool):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def _facet_values(record: dict[str, Any], candidates: tuple[str, ...]) -> list[str]:
    for field in candidates:
        value = record.get(field)
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        if isinstance(value, list):
            values = [str(item).strip() for item in value if str(item).strip()]
            if values:
                return values
    return []


def build(api_dir: Path, output_dir: Path) -> dict[str, Any]:
    shard_paths = sorted(
        api_dir.glob("catalog_summary_part*.json"),
        key=lambda path: int(SHARD_RE.fullmatch(path.name).group(1))
        if SHARD_RE.fullmatch(path.name)
        else 10**9,
    )
    if not shard_paths:
        raise ValueError("no catalog_summary_part*.json shards found")

    shard_index: list[dict[str, Any]] = []
    facet_counts: dict[str, Counter[str]] = {
        name: Counter() for name in FACET_FIELDS
    }
    field_presence: Counter[str] = Counter()
    field_types: dict[str, Counter[str]] = defaultdict(Counter)
    seen_ids: set[str] = set()
    duplicate_ids = 0
    records_without_stable_id = 0
    record_count = 0

    for path in shard_paths:
        match = SHARD_RE.fullmatch(path.name)
        if match is None:
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows = _records(payload)
        record_count += len(rows)

        for record in rows:
            identifier = _stable_id(record)
            if identifier is None:
                records_without_stable_id += 1
            elif identifier in seen_ids:
                duplicate_ids += 1
            else:
                seen_ids.add(identifier)

            for key, value in record.items():
                field_presence[key] += 1
                field_types[key][_json_type(value)] += 1
            for facet_name, candidates in FACET_FIELDS.items():
                facet_counts[facet_name].update(_facet_values(record, candidates))

        shard_index.append(
            {
                "part": int(match.group(1)),
                "path": f"api/{path.name}",
                "url": f"../{path.name}",
                "records": len(rows),
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
        )

    if [row["part"] for row in shard_index] != list(range(1, len(shard_index) + 1)):
        raise ValueError("catalog shard sequence is not contiguous")
    if duplicate_ids:
        raise ValueError(f"duplicate stable ids detected: {duplicate_ids}")

    output_dir.mkdir(parents=True, exist_ok=True)

    facets = {
        "schema_version": 1,
        "record_count": record_count,
        "facets": {
            name: [
                {"value": value, "count": count}
                for value, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))
            ]
            for name, counter in facet_counts.items()
        },
    }
    schema_profile = {
        "schema_version": 1,
        "record_count": record_count,
        "fields": [
            {
                "name": name,
                "present_count": field_presence[name],
                "presence_ratio": round(field_presence[name] / record_count, 6)
                if record_count
                else 0,
                "types": dict(sorted(field_types[name].items())),
            }
            for name in sorted(field_presence)
        ],
    }
    shards_payload = {
        "schema_version": 1,
        "record_count": record_count,
        "shard_count": len(shard_index),
        "shards": shard_index,
    }

    payloads = {
        "shards.json": shards_payload,
        "facets.json": facets,
        "schema-profile.json": schema_profile,
    }
    for name, payload in payloads.items():
        (output_dir / name).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    files = []
    for name in sorted(payloads):
        path = output_dir / name
        files.append(
            {
                "path": f"api/v1/{name}",
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
        )

    manifest = {
        "schema_version": 1,
        "distribution": "boothitemmanager-static-api-v1",
        "source": {
            "publisher": "BOOTH / individual shop owners",
            "service_url": "https://booth.pm/",
            "note": "This build does not fetch BOOTH. It indexes previously collected public listing metadata in the repository.",
        },
        "record_count": record_count,
        "unique_stable_id_count": len(seen_ids),
        "records_without_stable_id": records_without_stable_id,
        "shard_count": len(shard_index),
        "cache": {"strategy": "revalidate-manifest", "recommended_max_age_seconds": 3600},
        "files": files,
        "source_shards": shard_index,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-dir", type=Path, default=Path("api"))
    parser.add_argument("--output-dir", type=Path, default=Path("api/v1"))
    args = parser.parse_args(argv)
    manifest = build(args.api_dir, args.output_dir)
    print(
        f"built api/v1: {manifest['record_count']} records / "
        f"{manifest['shard_count']} shards / "
        f"{manifest['unique_stable_id_count']} unique stable ids"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
