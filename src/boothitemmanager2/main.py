import os
import uuid
from datetime import datetime

from .api_generator import generate_api
from .bridge import convert_ndjson_to_items
from .normalizer import normalize_html
from .similarity_engine import calculate_similar_items
from .staging_buffer import StagingBuffer
from .orchestrator import TransactionOrchestrator
from .storage import RawAssetPage


def run_pipeline():
    trace_id = str(uuid.uuid4())
    log_path = "acquisition.log"

    def log(msg):
        with open(log_path, "a") as f:
            f.write(f"[{datetime.now().isoformat()}] [Pipeline] {msg}\n")
        print(msg)

    log(f"🚀 Starting BoothItemManager2 Pipeline (Trace ID: {trace_id})")
    all_items_dict = {}
    ndjson_path = "data/raw/index.ndjson"
    if os.path.exists(ndjson_path):
        log(f"🌉 Ingesting data from {ndjson_path}...")
        block = convert_ndjson_to_items(ndjson_path, trace_id)
        if block.result == "SUCCESS":
            ndjson_items = block.actual_state.get("items", [])
            for item in ndjson_items:
                all_items_dict[item.item_id] = item
            log(f"✅ Ingested {len(ndjson_items)} items from bridge.")
    from pathlib import Path

    raw_dir = Path("input/raw")
    raw_files = list(raw_dir.glob("*.html"))
    if raw_files:
        log(
            f"📦 Processing {len(raw_files)} detailed HTML files..."
        )
        for rf in raw_files:
            item_id = rf.stem
            url = f"https://booth.pm/ja/items/{item_id}"
            content = rf.read_text(encoding="utf-8")
            raw_page = RawAssetPage(url=url, content=content, scraped_at=datetime.now())
            block = normalize_html(raw_page, trace_id)
            item = block.actual_state["item"]
            all_items_dict[item.item_id] = item
    items = list(all_items_dict.values())
    log(f"📊 Total items for processing: {len(items)}")

    # Intermediate Staging Buffer for expensive operations
    log("🔗 Computing item similarities (with caching)...")
    cache_key = "similarity_results"
    # Use item IDs and count as cache params
    cache_params = {"ids": sorted([i.item_id for i in items]), "count": len(items)}
    cached_result = StagingBuffer.get(cache_key, cache_params)

    if cached_result:
        log("♻️ Using cached similarity results.")
        from dataclasses import replace
        from .storage import ItemCategory, TagSet
        # Reconstruct items from cached similar_items
        sim_map = {r["id"]: r["sim"] for r in cached_result}
        for i in range(len(items)):
            if items[i].item_id in sim_map:
                items[i] = replace(items[i], similar_items=sim_map[items[i].item_id])
    else:
        sim_block = calculate_similar_items(items, trace_id)
        items = sim_block.actual_state["items"]
        # Save to buffer
        sim_to_cache = [{"id": i.item_id, "sim": i.similar_items} for i in items]
        StagingBuffer.set(cache_key, cache_params, sim_to_cache)
        log("💾 Similarity results cached.")

    graph_data = {"nodes": [], "edges": []}
    
    # 2-Phase Commit Orchestrator for atomic updates
    orchestrator = TransactionOrchestrator(trace_id)
    
    log("✨ Generating API in 'api/' directory...")
    # api_generator already has some internal atomicity for the 'api/' directory,
    # but let's use the orchestrator for the core data files as well.
    generate_api(items, graph_data, trace_id)
    
    # Prepare updates for Structured and Graph layers
    orchestrator.prepare("data/structured/catalog.json", [i.__dict__ for i in items])
    orchestrator.prepare("data/graph/nodes.json", graph_data["nodes"])
    orchestrator.prepare("data/graph/edges.json", graph_data["edges"])
    
    log("🔒 Committing transaction (2PC)...")
    orchestrator.commit()
    
    log("🏁 Pipeline complete.")


if __name__ == "__main__":
    run_pipeline()
