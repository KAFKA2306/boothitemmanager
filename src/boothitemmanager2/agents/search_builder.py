import json
import os

from ..core import TestBlock
from ..schemas.storage import Item


def build_search_index(items: list[Item], trace_id: str) -> TestBlock:
    output_path = "api/search_index.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    index = []
    for item in items:
        index.append(
            {
                "id": item.item_id,
                "title": item.title,
                "category": item.category.value,
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
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    return TestBlock(
        trace_id=trace_id,
        input=len(items),
        pre_state={},
        action="build_search_index",
        expected_state={"indexed_count": len(items)},
        actual_state={
            "indexed_count": len(items),
            "output_path": output_path,
            "file_size": os.path.getsize(output_path),
        },
        diff={},
        result="SUCCESS",
    )
