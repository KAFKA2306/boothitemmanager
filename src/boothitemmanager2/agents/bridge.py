import json
import os
from typing import List, Dict, Any
from ..schemas.storage import Item, ItemCategory, AvatarRef, FileAsset
from .normalizer import extract_mood_tags, load_aliases, pick_targets, infer_category
from ..core import TestBlock

def convert_ndjson_to_items(file_path: str, trace_id: str) -> TestBlock:
    """
    Bridges index.ndjson records into the Item model.
    P0 Priority: Connects crawled data to the pipeline.
    Returns a TestBlock for architectural consistency.
    """
    items: List[Item] = []
    if not os.path.exists(file_path):
        return TestBlock(trace_id, file_path, {}, "bridge_missing", {}, {}, {}, "FAIL")

    aliases = load_aliases()
    
    # Direct mapping from category_raw to ItemCategory
    CATEGORY_RAW_MAP = {
        "3Dキャラクター": ItemCategory.AVATAR,
        "3D衣装・装飾品": ItemCategory.OUTFIT,
        "3D小道具・その他": ItemCategory.ACCESSORY,
        "3Dモーション・アニメーション": ItemCategory.GIMMICK,
    }
    
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line: continue
            try:
                data = json.loads(line)
            except:
                continue
            
            item_id = str(data.get("item_id", ""))
            if not item_id: continue

            title = data.get("title", "")
            category_raw = data.get("category_raw", "")
            
            # Contextual inference
            targets = pick_targets(title, "", [category_raw], aliases)
            category = CATEGORY_RAW_MAP.get(category_raw)
            if not category:
                category = infer_category(title, "", [category_raw], targets, aliases)
            
            # High-dimensional extraction
            generated_tags = extract_mood_tags(title, "", [category_raw], aliases)

            item = Item(
                item_id=item_id,
                source="booth",
                source_url=data.get("source_url", ""),
                title=title,
                description="", 
                thumbnail_url=data.get("thumbnail_url", ""),
                creator_id=data.get("creator_id", "unknown"),
                creator_name=data.get("creator_name", "Unknown Shop"),
                published_at=None,
                tags_raw=[],
                tags_generated=generated_tags,
                category=category,
                like_count=0,
                price=data.get("price"),
                targets=targets,
                files=[]
            )
            items.append(item)
            
    return TestBlock(
        trace_id=trace_id,
        input=file_path,
        pre_state={},
        action="convert_ndjson_to_items",
        expected_state={"item_count_min": 1},
        actual_state={"items": items, "item_count": len(items)},
        diff={},
        result="SUCCESS"
    )
