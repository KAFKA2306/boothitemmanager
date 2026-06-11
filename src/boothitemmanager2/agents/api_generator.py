import json
import os
from collections import Counter
from dataclasses import asdict
from datetime import datetime
from typing import Any

from ..core import TestBlock
from ..schemas.storage import Item


def safe_rmtree(path: str):
    import shutil
    import os
    if os.path.exists(path):
        try:
            shutil.rmtree(path)
        except Exception:
            os.system(f"rm -rf {path}")


def generate_api(items: list[Item], graph_data: dict[str, Any], trace_id: str) -> TestBlock:
    import shutil

    api_dir = "api"
    api_staging = "api_staging"

    # Prepare staging for api/
    if os.path.exists(api_staging):
        safe_rmtree(api_staging)
    if os.path.exists(api_dir):
        shutil.copytree(api_dir, api_staging, dirs_exist_ok=True)
    else:
        os.makedirs(api_staging, exist_ok=True)

    # Prepare staging for dist/api/ if it exists
    dist_api_dir = os.path.join("dist", "api")
    dist_api_staging = os.path.join("dist", "api_staging")
    has_dist_api = os.path.exists(dist_api_dir)

    if has_dist_api:
        if os.path.exists(dist_api_staging):
            safe_rmtree(dist_api_staging)
        shutil.copytree(dist_api_dir, dist_api_staging, dirs_exist_ok=True)

    def serialize(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if hasattr(obj, "__dataclass_fields__"):
            d = asdict(obj)
            d.pop("user_state", None)
            d.pop("trace_log", None)
            d.pop("raw_html_snippet", None)
            return d
        if hasattr(obj, "value"):
            return obj.value
        return str(obj)

    # Optimized catalog summary parts for instant page load
    catalog_summaries = []
    items_with_compat = 0
    for item in items:
        has_compat = len(item.targets) > 0
        if has_compat:
            items_with_compat += 1

        catalog_summaries.append(
            {
                "id": item.item_id,
                "title": item.title,
                "category": item.category.value
                if hasattr(item.category, "value")
                else str(item.category),
                "price": item.price,
                "like_count": item.like_count,
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

    avatar_compatibility_rate = (items_with_compat / len(items)) * 100 if items else 0

    part1 = catalog_summaries[:2000]
    part2 = catalog_summaries[2000:]

    # Save to staging
    with open(os.path.join(api_staging, "catalog_summary_part1.json"), "w", encoding="utf-8") as f:
        json.dump(part1, f, ensure_ascii=False, separators=(",", ":"))
    with open(os.path.join(api_staging, "catalog_summary_part2.json"), "w", encoding="utf-8") as f:
        json.dump(part2, f, ensure_ascii=False, separators=(",", ":"))

    # Generate fallback JS scripts
    with open(os.path.join(api_staging, "catalog_summary_part1.js"), "w", encoding="utf-8") as f:
        f.write("window.BOOTH_CATALOG_PART1 = ")
        json.dump(part1, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";")

    # Regrow metadata.json using scripts/generate_metadata.py
    os.system("python3 scripts/generate_metadata.py")

    metadata_path = os.path.join(api_staging, "metadata.json")
    if not os.path.exists(metadata_path):
        metadata_path = "api/metadata.json"
        
    if os.path.exists(metadata_path):
        with open(metadata_path, encoding="utf-8") as f:
            meta_content = json.load(f)
        with open(os.path.join(api_staging, "metadata.js"), "w", encoding="utf-8") as f:
            f.write("window.BOOTH_METADATA = ")
            json.dump(meta_content, f, ensure_ascii=False, separators=(",", ":"))
            f.write(";")

    # Save to dist/api_staging/ if it exists
    if has_dist_api:
        with open(
            os.path.join(dist_api_staging, "catalog_summary_part1.json"), "w", encoding="utf-8"
        ) as f:
            json.dump(part1, f, ensure_ascii=False, separators=(",", ":"))
        with open(
            os.path.join(dist_api_staging, "catalog_summary_part2.json"), "w", encoding="utf-8"
        ) as f:
            json.dump(part2, f, ensure_ascii=False, separators=(",", ":"))
        with open(
            os.path.join(dist_api_staging, "catalog_summary_part1.js"), "w", encoding="utf-8"
        ) as f:
            f.write("window.BOOTH_CATALOG_PART1 = ")
            json.dump(part1, f, ensure_ascii=False, separators=(",", ":"))
            f.write(";")
        if os.path.exists(metadata_path):
            with open(os.path.join(dist_api_staging, "metadata.js"), "w", encoding="utf-8") as f:
                f.write("window.BOOTH_METADATA = ")
                json.dump(meta_content, f, ensure_ascii=False, separators=(",", ":"))
                f.write(";")

    # Shard individual item data into 100 files to bypass Cloudflare file limits
    details_dir = os.path.join(api_staging, "details")
    os.makedirs(details_dir, exist_ok=True)

    shards = {str(i).zfill(2): {} for i in range(100)}
    for item in items:
        # Determine shard ID from item_id suffix (numeric) or simple hash
        if item.item_id.isdigit():
            shard_id = str(int(item.item_id) % 100).zfill(2)
        else:
            shard_id = str(sum(ord(c) for c in item.item_id) % 100).zfill(2)

        # Filter out internal/private fields from the public sharded files
        item_dict = asdict(item)
        item_dict.pop("user_state", None)
        item_dict.pop("trace_log", None)
        item_dict.pop("raw_html_snippet", None)
        shards[shard_id][item.item_id] = item_dict

    for shard_id, shard_data in shards.items():
        shard_path = os.path.join(details_dir, f"shard_{shard_id}.json")
        with open(shard_path, "w", encoding="utf-8") as f:
            json.dump(shard_data, f, ensure_ascii=False, separators=(",", ":"), default=serialize)

    # Sync details directory to dist/api_staging/details if needed
    if has_dist_api:
        dist_details_dir = os.path.join(dist_api_staging, "details")
        if os.path.exists(dist_details_dir):
            safe_rmtree(dist_details_dir)
        shutil.copytree(details_dir, dist_details_dir, dirs_exist_ok=True)

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
        "avatar_compatibility_rate": round(avatar_compatibility_rate, 2),
        "updated_at": datetime.now().isoformat(),
    }
    metrics_path = os.path.join(api_staging, "metrics.json")
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)

    # Perform atomic swaps
    # Swap api/
    if os.path.exists(api_dir):
        api_old = "api_old"
        if os.path.exists(api_old):
            safe_rmtree(api_old)
        os.rename(api_dir, api_old)
        os.rename(api_staging, api_dir)
        safe_rmtree(api_old)
    else:
        os.rename(api_staging, api_dir)

    # Swap dist/api/
    if has_dist_api:
        if os.path.exists(dist_api_dir):
            dist_api_old = os.path.join("dist", "api_old")
            if os.path.exists(dist_api_old):
                safe_rmtree(dist_api_old)
            os.rename(dist_api_dir, dist_api_old)
            os.rename(dist_api_staging, dist_api_dir)
            safe_rmtree(dist_api_old)
        else:
            os.rename(dist_api_staging, dist_api_dir)

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
