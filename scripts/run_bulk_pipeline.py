"""Orchestrate the BoothItemManager2 bulk integration pipeline.

Flow: NDJSON bridge -> similarity -> DB -> graph -> search index ->
AI-related evidence report -> static API.
"""

from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from boothitemmanager2.ai_tool_detector import write_ai_tool_report
from boothitemmanager2.api_generator import generate_api
from boothitemmanager2.bridge import convert_ndjson_to_items
from boothitemmanager2.db_builder import build_db
from boothitemmanager2.graph_builder import build_graph
from boothitemmanager2.search_builder import build_search_index
from boothitemmanager2.similarity_engine import calculate_similar_items

NDJSON_PATH = "data/raw/index.ndjson"


def main() -> None:
    if not os.path.exists(NDJSON_PATH):
        print(f"❌ Error: {NDJSON_PATH} not found.")
        return

    print(f"🚀 [BRIDGE] Converting bulk data from {NDJSON_PATH}...")
    trace_id = f"bulk_{int(time.time())}"
    start_time = time.time()

    bridge_block = convert_ndjson_to_items(NDJSON_PATH, f"{trace_id}:bridge")
    items = bridge_block.actual_state["items"]
    print(f"✅ [BRIDGE] Converted {len(items)} items in {time.time() - start_time:.2f}s")

    print("\n🏗️ [BUILD] Finalizing data layers for bulk dataset...")

    print("  - Calculating item similarities...")
    similarity_block = calculate_similar_items(items, f"{trace_id}:similarity")
    items = similarity_block.actual_state["items"]

    print("  - Building DB...")
    build_db(items, f"{trace_id}:db")

    print("  - Building graph...")
    build_graph(items, f"{trace_id}:graph")

    print("  - Building search index...")
    build_search_index(items, f"{trace_id}:search")

    print("  - Detecting explicitly disclosed AI-related tools...")
    ai_report = write_ai_tool_report(items)
    print(
        "    "
        f"{ai_report['metrics']['candidate_items']} candidate items / "
        f"{ai_report['metrics']['candidate_shops']} shops"
    )

    print("  - Generating static API...")
    generate_api(items, {}, f"{trace_id}:api")

    print(f"\n✨ Bulk pipeline complete in {time.time() - start_time:.2f}s!")
    print(f"📊 Total items indexed: {len(items)}")


if __name__ == "__main__":
    main()
