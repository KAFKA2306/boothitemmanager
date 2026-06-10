import json
import os
from collections import Counter
from dataclasses import asdict
from datetime import datetime
from typing import Any

from ..core import TestBlock
from ..schemas.storage import Item


def generate_api(items: list[Item], graph_data: dict[str, Any], trace_id: str) -> TestBlock:
    api_dir = "api"
    items_dir = os.path.join(api_dir, "items")
    os.makedirs(items_dir, exist_ok=True)

    def serialize(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if hasattr(obj, "__dataclass_fields__"):
            return asdict(obj)
        if hasattr(obj, "value"):
            return obj.value
        return str(obj)

    catalog_path = os.path.join(api_dir, "catalog.json")
    with open(catalog_path, "w", encoding="utf-8") as f:
        json.dump(
            [asdict(item) for item in items], f, ensure_ascii=False, indent=2, default=serialize
        )
    summaries = []
    for item in items:
        summaries.append(
            {
                "item_id": item.item_id,
                "name": item.title,
                "shop_name": item.creator_name,
                "type": item.category.value,
                "image_url": item.thumbnail_url,
                "current_price": item.price,
                "like_count": item.like_count,
            }
        )
    all_items_path = os.path.join(items_dir, "all.json")
    with open(all_items_path, "w", encoding="utf-8") as f:
        json.dump(summaries, f, ensure_ascii=False, indent=2)
    for item in items:
        item_path = os.path.join(items_dir, f"{item.item_id}.json")
        with open(item_path, "w", encoding="utf-8") as f:
            json.dump(asdict(item), f, ensure_ascii=False, indent=2, default=serialize)
    type_counts = Counter(item.category.value for item in items)
    shop_counts = Counter(item.creator_name for item in items)
    avatar_list = []
    for item in items:
        for target in item.targets:
            avatar_list.append(target.name)
    avatar_counts = Counter(avatar_list)
    metrics = {
        "total_items": len(items),
        "types": dict(type_counts),
        "top_shops": dict(shop_counts.most_common(10)),
        "top_avatars": dict(avatar_counts.most_common(10)),
        "updated_at": datetime.now().isoformat(),
    }
    metrics_path = os.path.join(api_dir, "metrics.json")
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)
    return TestBlock(
        trace_id=trace_id,
        input=len(items),
        pre_state={},
        action="generate_api",
        expected_state={"file_count_min": 3},
        actual_state={"item_count": len(items), "api_dir": api_dir},
        diff={},
        result="SUCCESS",
    )
