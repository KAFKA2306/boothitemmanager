import os
import uuid
import json
from datetime import datetime
from .agents.crawler import fetch_html
from .agents.normalizer import normalize_html
from .agents.api_generator import generate_api
from .schemas.storage import RawAssetPage, Item

from .agents.bridge import convert_ndjson_to_items

def run_pipeline():
    """
    Orchestrates the BoothItemManager2 pipeline.
    Zero-Fat, Crash-Driven.
    """
    trace_id = str(uuid.uuid4())
    log_path = "acquisition.log"
    def log(msg):
        with open(log_path, "a") as f:
            f.write(f"[{datetime.now().isoformat()}] [Pipeline] {msg}\n")
        print(msg)

    log(f"🚀 Starting BoothItemManager2 Pipeline (Trace ID: {trace_id})")

    # 1. Load data from multiple sources
    all_items_dict = {}

    # Source A: index.ndjson (Bridge)
    ndjson_path = "data/raw/index.ndjson"
    if os.path.exists(ndjson_path):
        log(f"🌉 Ingesting data from {ndjson_path}...")
        block = convert_ndjson_to_items(ndjson_path, trace_id)
        if block.result == "SUCCESS":
            ndjson_items = block.actual_state.get("items", [])
            for item in ndjson_items:
                all_items_dict[item.item_id] = item
            log(f"✅ Ingested {len(ndjson_items)} items from bridge.")

    # Source B: input/raw/*.html (Detailed Crawler)
    from pathlib import Path
    raw_dir = Path("input/raw")
    raw_files = list(raw_dir.glob("*.html"))

    if raw_files:
        log(f"📦 Processing {len(raw_files)} detailed HTML files...")
        for rf in raw_files:
            item_id = rf.stem
            url = f"https://booth.pm/ja/items/{item_id}"
            content = rf.read_text(encoding='utf-8')
            raw_page = RawAssetPage(url=url, content=content, scraped_at=datetime.now())
            
            block = normalize_html(raw_page, trace_id)
            item = block.actual_state["item"]
            # Overwrite bridge data with more detailed HTML data if available
            all_items_dict[item.item_id] = item

    items = list(all_items_dict.values())
    log(f"📊 Total items for processing: {len(items)}")

    # 2. Build Graph & Search Index (TODO: Add these builders to the loop)
    # For now, we go straight to API generation
    graph_data = {"nodes": [], "edges": []}
    
    # 3. Generate API
    log(f"✨ Generating API in 'api/' directory...")
    generate_api(items, graph_data, trace_id)
    log(f"🏁 Pipeline complete.")

if __name__ == "__main__":
    run_pipeline()
