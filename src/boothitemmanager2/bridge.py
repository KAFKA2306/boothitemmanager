import json
import os

from .core import TestBlock
from .storage import Item, ItemCategory
from .normalizer import extract_tag_set, infer_category, load_aliases, pick_targets, _get_cached_likes


def convert_ndjson_to_items(file_path: str, trace_id: str) -> TestBlock:
    items: list[Item] = []
    if not os.path.exists(file_path):
        return TestBlock(trace_id, file_path, {}, "bridge_missing", {}, {}, {}, "FAIL")
    aliases = load_aliases()
    CATEGORY_RAW_MAP = {
        "3Dキャラクター": ItemCategory.AVATAR,
        "3D衣装・装飾品": ItemCategory.OUTFIT,
        "3D小道具・その他": ItemCategory.PROP,
        "3Dモーション・アニメーション": ItemCategory.ANIMATION,
        "VRoid": ItemCategory.VROID,
    }
    seen_ids = set()
    with open(file_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except Exception:
                continue
            item_id = str(data.get("item_id", ""))
            if not item_id or item_id in seen_ids:
                continue
            seen_ids.add(item_id)
            title = data.get("title", "")
            category_raw = data.get("category_raw", "")
            desc = data.get("description", "")
            targets = pick_targets(title, desc, [category_raw], aliases)
            category = CATEGORY_RAW_MAP.get(category_raw)
            if not category:
                category = infer_category(title, desc, [category_raw], targets, aliases)
            tag_set = extract_tag_set(title, desc, [category_raw], targets, aliases, category)
            from datetime import datetime

            trace_log = {
                "timestamp": datetime.now().isoformat(),
                "source_ndjson": file_path,
                "rules": {"bridge_conversion": "ndjson_to_item"},
            }
            # published_at resolution
            published_at = None
            html_path = f"input/raw/{item_id}.html"
            if os.path.exists(html_path):
                from bs4 import BeautifulSoup
                try:
                    with open(html_path, "r", encoding="utf-8") as html_f:
                        soup = BeautifulSoup(html_f.read(), "html.parser")
                    json_ld = None
                    json_ld_elem = soup.select_one("script[type='application/ld+json']")
                    if json_ld_elem:
                        try:
                            json_ld = json.loads(json_ld_elem.string)
                        except Exception:
                            pass
                    from .normalizer import _pick_published_at
                    published_at = _pick_published_at(soup, json_ld)
                except Exception:
                    pass
            if not published_at and data.get("crawled_at"):
                try:
                    published_at = datetime.fromisoformat(data["crawled_at"].replace("Z", "+00:00"))
                except Exception:
                    pass

            item = Item(
                item_id=item_id,
                source_url=data.get("source_url", ""),
                title=title,
                description=desc,
                thumbnail_url=data.get("thumbnail_url", ""),
                creator_id=data.get("creator_id", "unknown"),
                creator_name=data.get("creator_name", "Unknown Shop"),
                published_at=published_at,
                like_count=data.get("like_count") if data.get("like_count") is not None else _get_cached_likes(item_id),
                price=data.get("price"),
                category=category,
                tag_set=tag_set,
                similar_items=[],
                user_state={},
                tags_raw=[],
                targets=targets,
                files=[],
                audit_status="UNVERIFIED",
                trace_log=trace_log,
                raw_html_snippet=None,
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
        result="SUCCESS",
    )
