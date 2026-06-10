import json
import os
from typing import List
from ..schemas.storage import Item, ItemCategory
from .normalizer import extract_mood_tags, load_aliases

def ingest_ndjson(file_path: str) -> List[Item]:
    """
    Bridges index.ndjson records into the Item model.
    P0 Priority: Connects crawled data to the pipeline.
    Zero-Fat, Crash-Driven.
    """
    items = []
    if not os.path.exists(file_path):
        return items

    aliases = load_aliases()
    
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip(): continue
            data = json.loads(line)
            
            # Simple category mapping for now
            category_raw = data.get("category_raw", "").lower()
            category = ItemCategory.OTHER
            if "キャラクター" in category_raw or "アバター" in category_raw:
                category = ItemCategory.AVATAR
            elif "衣装" in category_raw:
                category = ItemCategory.OUTFIT
            elif "アクセサリー" in category_raw:
                category = ItemCategory.ACCESSORY
            elif "ツール" in category_raw or "システム" in category_raw:
                category = ItemCategory.GIMMICK

            # Extract mood tags from title
            title = data.get("title", "")
            mood_tags = extract_mood_tags(title, "", [], aliases)

            item = Item(
                item_id=data["item_id"],
                source="booth",
                source_url=data["source_url"],
                title=title,
                description="", # Missing in ndjson
                thumbnail_url=data.get("thumbnail_url", ""),
                creator_id=data.get("creator_id", "unknown"),
                creator_name=data.get("creator_name", "Unknown Shop"),
                published_at=None,
                tags_raw=[],
                tags_generated=mood_tags,
                category=category,
                like_count=0,
                price=data.get("price"),
            )
            items.append(item)
            
    return items
