from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.audit_static_api import audit, write_report


class StaticApiAuditTests(unittest.TestCase):
    def write_shard(self, root: Path, part: int, records: list[dict]) -> Path:
        path = root / f"catalog_summary_part{part}.json"
        path.write_text(json.dumps(records), encoding="utf-8")
        return path

    def test_valid_contiguous_shards(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_shard(root, 1, [{"id": 1}, {"id": 2}])
            self.write_shard(root, 2, [{"id": 3}])

            report = audit(root)

            self.assertEqual(report["error_count"], 0)
            self.assertEqual(report["record_count"], 3)
            self.assertEqual(report["unique_stable_id_count"], 3)
            self.assertEqual(len(report["files"][0]["sha256"]), 64)

    def test_duplicate_id_across_shards_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_shard(root, 1, [{"item_id": "42"}])
            self.write_shard(root, 2, [{"item_id": "42"}])

            report = audit(root)

            self.assertIn(
                "DUPLICATE_RECORD_ID",
                {problem["code"] for problem in report["problems"]},
            )

    def test_gap_and_size_limit_fail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_shard(root, 1, [{"id": 1}])
            self.write_shard(root, 3, [{"id": 3}])

            report = audit(root, max_bytes=1)
            codes = {problem["code"] for problem in report["problems"]}

            self.assertIn("NON_CONTIGUOUS_SHARDS", codes)
            self.assertIn("SHARD_TOO_LARGE", codes)

    def test_report_write_is_atomic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report_path = Path(directory) / "build" / "audit.json"
            write_report({"schema_version": 1}, report_path)

            self.assertEqual(
                json.loads(report_path.read_text(encoding="utf-8")),
                {"schema_version": 1},
            )
            self.assertFalse(report_path.with_suffix(".json.tmp").exists())


if __name__ == "__main__":
    unittest.main()
