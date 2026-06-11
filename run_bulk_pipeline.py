"""
run_bulk_pipeline.py - Orchestrates bulk data integration for BoothItemManager2
Orchestrates: Bridge (ndjson -> Item) -> DB -> Graph -> Search Index -> API
"""

import os
import sys
import time

sys.path.insert(0, os.path.abspath("."))

from src.boothitemmanager2.agents import build_db, build_graph, build_search_index, generate_api
from src.boothitemmanager2.agents.bridge import convert_ndjson_to_items
from src.boothitemmanager2.agents.similarity_engine import calculate_similar_items

NDJSON_PATH = "data/raw/index.ndjson"


def main():
    if not os.path.exists(NDJSON_PATH):
        print(f"❌ Error: {NDJSON_PATH} not found.")
        return

    print(f"🚀 [BRIDGE] Converting bulk data from {NDJSON_PATH}...")
    trace_id = f"bulk_{int(time.time())}"

    start_time = time.time()
    bridge_block = convert_ndjson_to_items(NDJSON_PATH, f"{trace_id}:bridge")
    items = bridge_block.actual_state["items"]

    elapsed = time.time() - start_time
    print(f"✅ [BRIDGE] Converted {len(items)} items in {elapsed:.2f}s")

    print("\n🏗️ [BUILD] Finalizing Data Layers for bulk dataset...")

    # Similarity Engine
    print("  - Calculating Item Similarities...")
    similarity_block = calculate_similar_items(items, f"{trace_id}:similarity")
    items = similarity_block.actual_state["items"]

    # 3. Build DB
    print("  - Building DB...")
    build_db(items, f"{trace_id}:db")

    # 4. Build Graph
    print("  - Building Graph (this might take a moment)...")
    build_graph(items, f"{trace_id}:graph")

    # 5. Build Search Index
    print("  - Building Search Index...")
    build_search_index(items, f"{trace_id}:search")

    # 6. Generate Static API
    print("  - Generating API...")
    generate_api(items, {}, f"{trace_id}:api")

    total_elapsed = time.time() - start_time
    print(f"\n✨ Bulk pipeline complete in {total_elapsed:.2f}s!")
    print(f"📊 Total items indexed: {len(items)}")


if __name__ == "__main__":
    main()
