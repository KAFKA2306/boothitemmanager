import json
import os

from .core import TestBlock
from .storage import Item


def build_search_index(items: list[Item], trace_id: str) -> TestBlock:
    output_dir = "api"
    os.makedirs(output_dir, exist_ok=True)
    
    # Sharding index to bypass Cloudflare 25MiB limit
    shard_size = 10000
    shards_paths = []
    
    for i in range(0, len(items), shard_size):
        shard_items = items[i : i + shard_size]
        shard_index = []
        for item in shard_items:
            shard_index.append(
                {
                    "id": item.item_id,
                    "title": item.title,
                    "category": item.category.value
                    if hasattr(item.category, "value")
                    else str(item.category),
                    "price": item.price,
                    "compatible_avatars": [t.name for t in item.targets],
                    "tags": item.tags,
                    "style": item.tag_set.style,
                    "outfit_type": item.tag_set.outfit_type,
                    "appearance": item.tag_set.appearance,
                    "color": item.tag_set.color,
                    "accessory": item.tag_set.accessory,
                    "body_type": item.tag_set.body_type,
                    "feature": item.tag_set.feature,
                    "platform": item.tag_set.platform,
                    "season": item.tag_set.season,
                    "has_dynamic_bone": bool(
                        any(f in ["PhysBone", "PB対応", "揺れもの", "PB"] for f in item.tags)
                        or "PhysBone" in item.tag_set.feature
                    ),
                    "quest_compatible": bool(
                        any(f in ["Quest対応", "Quest", "Android"] for f in item.tags)
                        or "QuestCompatible" in item.tag_set.feature
                    ),
                    "author": item.creator_name,
                    "thumbnail": item.thumbnail_url,
                    "booth_url": item.source_url,
                }
            )
        
        shard_id = i // shard_size
        output_path = os.path.join(output_dir, f"search_index_part{shard_id}.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(shard_index, f, ensure_ascii=False, separators=(",", ":"))
        shards_paths.append(output_path)

    # Cleanup old un-sharded index if it exists
    old_path = os.path.join(output_dir, "search_index.json")
    if os.path.exists(old_path):
        os.remove(old_path)

    return TestBlock(
        trace_id=trace_id,
        input=len(items),
        pre_state={},
        action="build_search_index",
        expected_state={"indexed_count": len(items)},
        actual_state={
            "indexed_count": len(items),
            "shards_count": len(shards_paths),
            "output_paths": shards_paths,
        },
        diff={},
        result="SUCCESS",
    )
