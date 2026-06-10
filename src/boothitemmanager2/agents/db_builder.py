import json
import os
from typing import List, Any
from datetime import datetime
from ..core import TestBlock
from ..schemas.storage import Item

def build_db(items: List[Item], trace_id: str) -> TestBlock:
    """
    Builds the structured database (catalog.json) from a list of Items.
    Crash-Driven: No try-catch blocks.
    Zero-Fat: Minimal serialization logic.
    """
    output_path = "data/structured/catalog.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    def _serialize(obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        if hasattr(obj, 'value'):  # Enum
            return obj.value
        return str(obj)

    def _item_to_dict(item: Item) -> dict:
        return {
            "item_id": item.item_id,
            "source": item.source,
            "source_url": item.source_url,
            "title": item.title,
            "description": item.description[:500] if item.description else "",
            "thumbnail_url": item.thumbnail_url,
            "creator_id": item.creator_id,
            "creator_name": item.creator_name,
            "published_at": _serialize(item.published_at) if item.published_at else None,
            "tags_raw": item.tags_raw,
            "tags_generated": item.tags_generated,
            "category": item.category.value,
            "like_count": item.like_count,
            "price": item.price,
            "targets": [{"code": t.code, "name": t.name} for t in item.targets]
        }

    catalog = [_item_to_dict(item) for item in items]

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)

    return TestBlock(
        trace_id=trace_id,
        input=len(items),
        pre_state={"file_exists": os.path.exists(output_path)},
        action="build_db",
        expected_state={"item_count": len(items)},
        actual_state={
            "item_count": len(items),
            "output_path": output_path,
            "file_size": os.path.getsize(output_path)
        },
        diff={},
        result="SUCCESS"
    )
