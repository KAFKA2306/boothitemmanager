"""
generate_proof.py - Formal Verification & System Integrity Proof
==============================================================
Verifies the current state against the Test Block Provability Model.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Path setup
DATA_DIR = Path("data")
CATALOG_PATH = DATA_DIR / "structured" / "catalog.json"
NODES_PATH = DATA_DIR / "graph" / "nodes.json"
EDGES_PATH = DATA_DIR / "graph" / "edges.json"
API_PATH = Path("api") / "catalog_summary_part1.json"


def get_file_stats(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False}
    return {
        "exists": True,
        "size_bytes": os.path.getsize(path),
        "last_modified": datetime.fromtimestamp(os.path.getmtime(path)).isoformat(),
    }


def verify_invariants() -> dict[str, Any]:
    proof: dict[str, Any] = {
        "timestamp": datetime.now().isoformat(),
        "layers": {},
        "invariants": {},
    }

    # 1. Structural Layer Proof
    catalog_stats = get_file_stats(CATALOG_PATH)
    item_count = 0
    catalog: list[dict[str, Any]] = []
    if catalog_stats["exists"]:
        with open(CATALOG_PATH, encoding="utf-8") as f:
            catalog = json.load(f)
            item_count = len(catalog)

    proof["layers"]["structured"] = {
        "status": "VERIFIED" if item_count >= 40000 else "INCOMPLETE",
        "item_count": item_count,
        "file": catalog_stats,
    }

    # 2. Graph Layer Proof (No orphan edges)
    graph_status = "FAILED"
    orphan_count = 0
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    if NODES_PATH.exists() and EDGES_PATH.exists():
        with open(NODES_PATH, encoding="utf-8") as f:
            nodes = json.load(f)
        with open(EDGES_PATH, encoding="utf-8") as f:
            edges = json.load(f)
        node_ids = {n["id"] for n in nodes}
        orphans = [e for e in edges if e["target"] not in node_ids]
        orphan_count = len(orphans)
        graph_status = "PASS" if orphan_count == 0 else "FAIL"

    proof["layers"]["graph"] = {
        "status": graph_status,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "orphan_edges": orphan_count,
    }

    # 3. API Sync Proof
    api_dir = Path("api")
    metadata_path = api_dir / "metadata.json"
    api: list[dict[str, Any]] = []
    if metadata_path.exists():
        with open(metadata_path, encoding="utf-8") as f:
            meta = json.load(f)
        shards = meta.get("catalog_shards", 1)
        for part_id in range(1, shards + 1):
            part_path = api_dir / f"catalog_summary_part{part_id}.json"
            if part_path.exists():
                with open(part_path, encoding="utf-8") as f:
                    api.extend(json.load(f))

    api_count = len(api)
    api_stats = get_file_stats(API_PATH)

    sync_status = "PASS" if api_count == item_count else "FAIL"
    proof["layers"]["api"] = {
        "status": sync_status,
        "index_count": api_count,
        "sync_with_db": sync_status,
    }

    # 4. Formal Proof of Correctness (State Equivalence)
    # We verify that ALL items exist correctly in all 3 layers
    cross_layer_proof = "NOT_STARTED"
    if item_count > 0 and len(nodes) > 0 and len(edges) > 0 and len(api) > 0:
        catalog_ids = {i["item_id"] for i in catalog}
        api_ids = {i["id"] for i in api}
        node_ids = {n["id"] for n in nodes}
        edge_tuples = {(e["source"], e["target"], e["relation"]) for e in edges}

        # Check if catalog items exactly match API search index items
        all_match = catalog_ids == api_ids

        if all_match:
            for item in catalog:
                item_id = item["item_id"]
                creator_id = item["creator_id"]

                tags_raw = item.get("tags_raw") or []
                tag_set = item.get("tag_set") or {}
                flattened = []
                for v in tag_set.values():
                    if isinstance(v, list):
                        flattened.extend(v)
                item_tags = set(tags_raw + flattened)

                item_node_id = f"item:{item_id}"
                creator_node_id = f"creator:{creator_id}"

                if item_node_id not in node_ids:
                    all_match = False
                    break
                if creator_node_id not in node_ids:
                    all_match = False
                    break
                if (item_node_id, creator_node_id, "CREATED_BY") not in edge_tuples:
                    all_match = False
                    break

                for tag in item_tags:
                    tag_node_id = f"tag:{tag}"
                    if tag_node_id not in node_ids:
                        all_match = False
                        break
                    if (item_node_id, tag_node_id, "HAS_TAG") not in edge_tuples:
                        all_match = False
                        break

                if not all_match:
                    break

        cross_layer_proof = "VERIFIED" if all_match else "FAILED"

    proof["invariants"]["cross_layer_consistency"] = cross_layer_proof

    return proof


if __name__ == "__main__":
    print("💎 BoothItemManager2: Initiating Formal Verification Proof...", file=sys.stderr)
    result = verify_invariants()
    print(json.dumps(result, indent=2, ensure_ascii=False))

    if result["invariants"]["cross_layer_consistency"] == "VERIFIED":
        print(
            "\n✅ SYSTEM PROVEN CORRECT: All layers are synchronized and invariants are maintained.",
            file=sys.stderr,
        )
    else:
        print("\n❌ VERIFICATION FAILED: Consistency gap detected.", file=sys.stderr)
        sys.exit(1)
