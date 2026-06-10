import os
import uuid
from datetime import datetime

from .agents.api_generator import generate_api
from .agents.bridge import convert_ndjson_to_items
from .agents.normalizer import normalize_html
from .agents.similarity_engine import calculate_similar_items
from .schemas.storage import RawAssetPage


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
            f"📦 Processing {len(raw_files)} detailed HTML files (limiting to 100 for verification)..."
        )
        for rf in raw_files[:100]:
            item_id = rf.stem
            url = f"https://booth.pm/ja/items/{item_id}"
            content = rf.read_text(encoding="utf-8")
            raw_page = RawAssetPage(url=url, content=content, scraped_at=datetime.now())
            block = normalize_html(raw_page, trace_id)
            item = block.actual_state["item"]
            all_items_dict[item.item_id] = item
    items = list(all_items_dict.values())
    log(f"📊 Total items for processing: {len(items)}")
    log("🔗 Computing item similarities...")
    sim_block = calculate_similar_items(items, trace_id)
    items = sim_block.actual_state["items"]
    graph_data = {"nodes": [], "edges": []}
    log("✨ Generating API in 'api/' directory...")
    generate_api(items, graph_data, trace_id)
    log("🏁 Pipeline complete.")


if __name__ == "__main__":
    run_pipeline()
