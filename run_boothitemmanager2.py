"""
run_boothitemmanager2.py - Master Orchestrator for BoothItemManager2 Perfect Copy
===============================================================
Orchestrates: Crawler -> Normalizer -> DB/Graph Builder -> API/Search Index
Usage: python run_boothitemmanager2.py
"""
import sys
import time
import os
from datetime import datetime

# Ensure project root is in path
sys.path.insert(0, os.path.abspath('.'))

from src.boothitemmanager2.agents import (
    fetch_html, 
    normalize_html, 
    build_db, 
    build_graph, 
    build_search_index, 
    generate_api,
    tag_graph_builder
)

# Target IDs for the initial collection (Representing the core requested items)
ITEM_IDS = [
    '3984867', # Aoi
    '4213786', # INABA/Shiina/KitsuneAme Set
    '4281941', # Shiina clothes
    '4414941', # KIMONO
    '4837941', # TAKOASHI armor
]

def main():
    print("🚀 BoothItemManager2: Initializing Perfect Copy Pipeline...")
    
    items = []
    trace_id_base = f"run_{int(time.time())}"
    
    for iid in ITEM_IDS:
        url = f"https://booth.pm/ja/items/{iid}"
        print(f"📡 [CRAWL] {url}")
        
        try:
            # 1. Fetch
            fetch_trace = f"{trace_id_base}:fetch:{iid}"
            block = fetch_html(url, fetch_trace)
            raw_page = block.actual_state['raw_page']
            
            # 2. Normalize
            norm_trace = f"{trace_id_base}:norm:{iid}"
            nb = normalize_html(raw_page, norm_trace)
            item = nb.actual_state['item']
            items.append(item)
            
            print(f"✅ [NORM]  Captured: {item.title[:50]}...")
            print(f"         Category: {item.category.value} | Targets: {[t.code for t in item.targets]}")
            
        except Exception as e:
            print(f"❌ [ERROR] Failed to process {iid}: {e}")
        
        # Be nice to BOOTH
        time.sleep(1)

    print("\n🏗️ [BUILD] Finalizing Data Layers...")
    
    # 3. Build DB
    build_db(items, f"{trace_id_base}:db")
    
    # 4. Build Graph
    build_graph(items, f"{trace_id_base}:graph")
    
    # 4b. Build Tag Graph (Discovery Layer)
    print("  - Building Tag Relationship Graph...")
    tag_graph_builder.build_tag_graph(items, f"{trace_id_base}:tag_graph")
    
    # 5. Build Search Index
    build_search_index(items, f"{trace_id_base}:search")
    
    # 6. Generate Static API
    generate_api(items, {}, f"{trace_id_base}:api")

    print("\n✨ BoothItemManager2 Perfect Copy is ready!")
    print(f"📊 Total items indexed: {len(items)}")
    print(f"📁 Dashboard: {os.path.abspath('index.html')}")
    print("🚀 Run a local server to view (e.g., 'python3 -m http.server 8000')")

if __name__ == "__main__":
    main()
