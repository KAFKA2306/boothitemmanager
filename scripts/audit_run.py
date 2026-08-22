import json
import os
import sys
from datetime import datetime
from typing import Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from boothitemmanager2.storage import Item, ItemCategory, TagSet, AvatarRef
from boothitemmanager2.quantitative_auditor import (
    QuantitativeAuditor,
    format_report,
    CrawlStats,
    FilterEvidence,
    FeatureStats,
)


def run_audit():
    catalog_path = "data/structured/catalog.json"
    if not os.path.exists(catalog_path):
        print(f"❌ Error: {catalog_path} not found.")
        sys.exit(1)

    with open(catalog_path, "r", encoding="utf-8") as f:
        catalog_data = json.load(f)

    items = []
    for data in catalog_data:
        # tag_set
        ts_data = data.get("tag_set") or {}
        tag_set = TagSet(
            appearance=ts_data.get("appearance", []),
            body_type=ts_data.get("body_type", []),
            style=ts_data.get("style", []),
            color=ts_data.get("color", []),
            outfit_type=ts_data.get("outfit_type", []),
            accessory=ts_data.get("accessory", []),
            feature=ts_data.get("feature", []),
            platform=ts_data.get("platform", []),
            season=ts_data.get("season", []),
            avatar_link=ts_data.get("avatar_link", []),
            material_property=ts_data.get("material_property", []),
            niche_subculture=ts_data.get("niche_subculture", []),
            activity_scene=ts_data.get("activity_scene", []),
        )

        # targets
        targets = []
        for t in data.get("targets", []):
            if isinstance(t, dict):
                targets.append(AvatarRef(code=t.get("code", ""), name=t.get("name", "")))
            elif isinstance(t, str):
                targets.append(AvatarRef(code=t, name=t))

        # published_at
        pub_at = None
        pub_str = data.get("published_at")
        if pub_str:
            try:
                pub_at = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
            except Exception:
                pass

        # category
        cat_str = data.get("category")
        category = (
            ItemCategory[cat_str] if cat_str in ItemCategory.__members__ else ItemCategory.ASSET
        )

        item = Item(
            item_id=str(data.get("item_id", "")),
            source_url=data.get("source_url", ""),
            title=data.get("title", ""),
            description=data.get("description", ""),
            thumbnail_url=data.get("thumbnail_url", ""),
            creator_id=data.get("creator_id", ""),
            creator_name=data.get("creator_name", ""),
            published_at=pub_at,
            like_count=data.get("like_count"),
            price=data.get("price"),
            category=category,
            tag_set=tag_set,
            similar_items=data.get("similar_items", []),
            user_state=data.get("user_state", {}),
            tags_raw=data.get("tags_raw", []),
            targets=targets,
            files=data.get("files", []),
            audit_status=data.get("audit_status", "UNVERIFIED"),
            trace_log=data.get("trace_log", {}),
            raw_html_snippet=data.get("raw_html_snippet"),
        )
        items.append(item)

    print(f"Loaded {len(items)} items for auditing.")

    # Calculate some stats for feature/filter mock/real counts
    color_search = sum(1 for i in items if i.tag_set.color)
    style_search = sum(1 for i in items if i.tag_set.style)
    avatar_rev_search = sum(1 for i in items if i.targets)
    cross_category_search = sum(1 for i in items if i.tag_set.outfit_type and i.tag_set.color)

    # Crawl status: source_items is from raw crawled pages, let's assume 40317
    crawl_stats = CrawlStats(source_items=40317, indexed_items=len(items))

    # Filters: count how many items matched year/popularity/category filters
    filters = FilterEvidence(
        year_filter_count=sum(1 for i in items if i.published_at and i.published_at.year == 2026),
        popularity_filter_count=sum(1 for i in items if i.like_count and i.like_count > 100),
        category_filter_count=sum(1 for i in items if i.category != ItemCategory.ASSET),
    )

    features = FeatureStats(
        color_search=color_search,
        style_search=style_search,
        avatar_reverse_search=avatar_rev_search,
        cross_category_search=cross_category_search,
    )

    auditor = QuantitativeAuditor()
    report = auditor.run(items, crawl=crawl_stats, filters=filters, features=features)

    print(format_report(report))


if __name__ == "__main__":
    run_audit()
