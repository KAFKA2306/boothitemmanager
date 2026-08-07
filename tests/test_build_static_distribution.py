from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_static_distribution import build


class StaticDistributionTests(unittest.TestCase):
    def write_shard(self, root: Path, part: int, rows: list[dict]) -> None:
        (root / f"catalog_summary_part{part}.json").write_text(
            json.dumps(rows, ensure_ascii=False), encoding="utf-8"
        )

    def test_builds_manifest_facets_and_schema_profile(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            api_dir = root / "api"
            output_dir = api_dir / "v1"
            api_dir.mkdir()
            self.write_shard(
                api_dir,
                1,
                [
                    {"id": 1, "category": "衣装", "shop_name": "A", "price": 1000},
                    {"id": 2, "category": "衣装", "shop_name": "B", "price": 1200},
                ],
            )
            self.write_shard(
                api_dir,
                2,
                [{"id": 3, "category": "ギミック", "shop_name": "A", "price": 0}],
            )

            manifest = build(api_dir, output_dir)

            self.assertEqual(manifest["record_count"], 3)
            self.assertEqual(manifest["shard_count"], 2)
            self.assertEqual(manifest["unique_stable_id_count"], 3)
            self.assertEqual(manifest["records_without_stable_id"], 0)

            facets = json.loads((output_dir / "facets.json").read_text(encoding="utf-8"))
            self.assertEqual(facets["facets"]["category"][0], {"value": "衣装", "count": 2})

            schema_profile = json.loads(
                (output_dir / "schema-profile.json").read_text(encoding="utf-8")
            )
            id_field = next(row for row in schema_profile["fields"] if row["name"] == "id")
            self.assertEqual(id_field["presence_ratio"], 1.0)
            self.assertEqual(id_field["types"], {"integer": 3})

    def test_duplicate_stable_id_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            api_dir = root / "api"
            api_dir.mkdir()
            self.write_shard(api_dir, 1, [{"item_id": "42"}])
            self.write_shard(api_dir, 2, [{"item_id": "42"}])

            with self.assertRaisesRegex(ValueError, "duplicate stable ids"):
                build(api_dir, api_dir / "v1")

    def test_non_contiguous_shards_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            api_dir = root / "api"
            api_dir.mkdir()
            self.write_shard(api_dir, 1, [{"id": 1}])
            self.write_shard(api_dir, 3, [{"id": 3}])

            with self.assertRaisesRegex(ValueError, "not contiguous"):
                build(api_dir, api_dir / "v1")


if __name__ == "__main__":
    unittest.main()
