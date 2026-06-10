import json
import os
import sys

sys.path.insert(0, os.path.abspath('.'))

from src.boothitemmanager2.agents.bridge import convert_ndjson_to_items

def test_bridge_deduplication():
    temp_ndjson = "scratch/temp_duplicates.ndjson"
    os.makedirs("scratch", exist_ok=True)
    with open(temp_ndjson, "w", encoding="utf-8") as f:
        f.write('{"item_id": "1", "title": "A", "category_raw": "3Dキャラクター"}\n')
        f.write('{"item_id": "2", "title": "B", "category_raw": "3Dキャラクター"}\n')
        f.write('{"item_id": "1", "title": "A Duplicate", "category_raw": "3Dキャラクター"}\n')
        
    try:
        block = convert_ndjson_to_items(temp_ndjson, "test_trace")
        items = block.actual_state["items"]
        item_ids = [item.item_id for item in items]
        print(f"Ingested item IDs: {item_ids}")
        assert len(items) == 2, f"Expected 2 unique items, got {len(items)}"
        assert "1" in item_ids
        assert "2" in item_ids
        print("✅ Ingestion deduplication test passed!")
    finally:
        if os.path.exists(temp_ndjson):
            os.remove(temp_ndjson)

def test_catalog_uniqueness():
    catalog_path = "api/catalog.json"
    if os.path.exists(catalog_path):
        with open(catalog_path, "r", encoding="utf-8") as f:
            items = json.load(f)
        item_ids = [item.get("item_id") for item in items if "item_id" in item]
        assert len(item_ids) == len(set(item_ids)), f"Catalog has duplicates! Total: {len(item_ids)}, Unique: {len(set(item_ids))}"
        print(f"✅ Catalog uniqueness test passed! Verified {len(item_ids)} items.")
    else:
        print("⚠️ catalog.json not found, skipping check.")

if __name__ == "__main__":
    test_bridge_deduplication()
    test_catalog_uniqueness()
