#!/usr/bin/env python3
"""Audit published catalog shards without external dependencies."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

SHARD_RE = re.compile(r"catalog_summary_part(\d+)\.json$")
ID_FIELDS = ("id", "item_id", "product_id", "booth_id")


@dataclass(frozen=True)
class Problem:
    code: str
    path: str
    detail: str
    record_index: int | None = None


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def records_from(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        for key in ("items", "products", "records", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                return [row for row in value if isinstance(row, dict)]
    raise ValueError("top level must be a list or contain items/products/records/data")


def stable_id(record: dict[str, Any]) -> str | None:
    for field in ID_FIELDS:
        value = record.get(field)
        if isinstance(value, (str, int)) and str(value).strip():
            return f"{field}:{str(value).strip()}"
    return None


def audit(api_dir: Path, *, max_bytes: int = 4_500_000) -> dict[str, Any]:
    shard_paths = sorted(
        api_dir.glob("catalog_summary_part*.json"),
        key=lambda path: int(SHARD_RE.search(path.name).group(1))
        if SHARD_RE.search(path.name)
        else 10**9,
    )
    problems: list[Problem] = []
    seen_ids: dict[str, tuple[str, int]] = {}
    files: list[dict[str, Any]] = []
    expected_part = 1
    total_records = 0

    if not shard_paths:
        problems.append(Problem("NO_SHARDS", str(api_dir), "no catalog shards found"))

    for path in shard_paths:
        match = SHARD_RE.fullmatch(path.name)
        if not match:
            continue
        part = int(match.group(1))
        if part != expected_part:
            problems.append(
                Problem(
                    "NON_CONTIGUOUS_SHARDS",
                    str(path),
                    f"expected part {expected_part}, found {part}",
                )
            )
            expected_part = part
        expected_part += 1

        size = path.stat().st_size
        if size > max_bytes:
            problems.append(
                Problem("SHARD_TOO_LARGE", str(path), f"{size} bytes exceeds {max_bytes}")
            )

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            records = records_from(payload)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            problems.append(Problem("INVALID_SHARD", str(path), str(exc)))
            records = []

        total_records += len(records)
        missing_id_count = 0
        for index, record in enumerate(records):
            identifier = stable_id(record)
            if identifier is None:
                missing_id_count += 1
                continue
            previous = seen_ids.get(identifier)
            if previous:
                problems.append(
                    Problem(
                        "DUPLICATE_RECORD_ID",
                        str(path),
                        f"{identifier} already appears in {previous[0]}[{previous[1]}]",
                        index,
                    )
                )
            else:
                seen_ids[identifier] = (str(path), index)

        files.append(
            {
                "path": str(path),
                "part": part,
                "bytes": size,
                "sha256": sha256(path),
                "records": len(records),
                "records_without_stable_id": missing_id_count,
            }
        )

    return {
        "schema_version": 1,
        "api_dir": str(api_dir),
        "file_count": len(files),
        "record_count": total_records,
        "unique_stable_id_count": len(seen_ids),
        "error_count": len(problems),
        "files": files,
        "problems": [asdict(problem) for problem in problems],
    }


def write_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("api_dir", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--max-bytes", type=int, default=4_500_000)
    args = parser.parse_args(argv)

    report = audit(args.api_dir, max_bytes=args.max_bytes)
    write_report(report, args.report)
    print(
        f"audited {report['file_count']} shards / {report['record_count']} records; "
        f"errors={report['error_count']}"
    )
    return 1 if report["error_count"] else 0


if __name__ == "__main__":
    sys.exit(main())
