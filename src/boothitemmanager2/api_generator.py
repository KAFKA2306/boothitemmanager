import json
import os
import shutil
import subprocess
from collections import Counter
from dataclasses import asdict
from datetime import datetime
from typing import Any

from .core import TestBlock
from .storage import Item


def safe_rmtree(path: str):
    if os.path.exists(path):
        shutil.rmtree(path)


def generate_api(items: list[Item], graph_data: dict[str, Any], trace_id: str) -> TestBlock:
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

    # Consistently shard into 5000-item blocks to stay under 25MiB
    shard_size = 5000
    for i in range(0, len(catalog_summaries), shard_size):
        part_id = (i // shard_size) + 1
        part_data = catalog_summaries[i : i + shard_size]

        with open(
            os.path.join(api_staging, f"catalog_summary_part{part_id}.json"), "w", encoding="utf-8"
        ) as f:
            json.dump(part_data, f, ensure_ascii=False, separators=(",", ":"))

        if has_dist_api:
            with open(
                os.path.join(dist_api_staging, f"catalog_summary_part{part_id}.json"),
                "w",
                encoding="utf-8",
            ) as f:
                json.dump(part_data, f, ensure_ascii=False, separators=(",", ":"))

    total_shards = (len(catalog_summaries) + shard_size - 1) // shard_size

    subprocess.run(["python3", "scripts/generate_metadata.py"], check=True)

    metadata_path = os.path.join(api_staging, "metadata.json")
    if not os.path.exists(metadata_path):
        raise FileNotFoundError(f"canonical metadata is missing: {metadata_path}")

    with open(metadata_path, encoding="utf-8") as f:
        meta_content = json.load(f)

    meta_content["catalog_shards"] = total_shards
    with open(os.path.join(api_staging, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(meta_content, f, ensure_ascii=False, indent=2)

    # Shard individual item data into 100 files to bypass Cloudflare file limits
    details_dir = os.path.join(api_staging, "details")
    os.makedirs(details_dir, exist_ok=True)

    shards = {str(i).zfill(2): {} for i in range(100)}
    for item in items:
        if item.item_id.isdigit():
            shard_id = str(int(item.item_id) % 100).zfill(2)
        else:
            shard_id = str(sum(ord(c) for c in item.item_id) % 100).zfill(2)

        item_dict = asdict(item)
        item_dict.pop("user_state", None)
        item_dict.pop("trace_log", None)
        item_dict.pop("raw_html_snippet", None)
        shards[shard_id][item.item_id] = item_dict

    for shard_id, shard_data in shards.items():
        shard_path = os.path.join(details_dir, f"shard_{shard_id}.json")
        with open(shard_path, "w", encoding="utf-8") as f:
            json.dump(shard_data, f, ensure_ascii=False, separators=(",", ":"), default=serialize)

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

    if os.path.exists(api_dir):
        api_old = "api_old"
        if os.path.exists(api_old):
            safe_rmtree(api_old)
        os.rename(api_dir, api_old)
        os.rename(api_staging, api_dir)
        safe_rmtree(api_old)
    else:
        os.rename(api_staging, api_dir)

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
