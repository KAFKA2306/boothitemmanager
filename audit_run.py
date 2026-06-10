"""
audit_run.py  ─  BoothItemManager2定量監査CLI
======================================
使い方:
  python audit_run.py --catalog data/structured/catalog.json
  python audit_run.py --catalog data/structured/catalog.json --source-items 500 \
      --year-filter 120 --popularity-filter 80 --category-filter 200 \
      --color-search 300 --style-search 150 \
      --avatar-reverse-search 400 --cross-category-search 350

ルール:
  * すべて数値出力（非数値禁止）
  * 未確認は 0 / Unknown
  * 推測補完禁止
"""
import argparse
import json
import sys
from datetime import datetime
from typing import List

from src.boothitemmanager2.agents import (
    QuantitativeAuditor,
    CrawlStats,
    FilterEvidence,
    FeatureStats,
    format_report,
)
from src.boothitemmanager2.schemas.storage import (
    Item,
    ItemCategory,
    AvatarRef,
    FileAsset,
)


# ---------------------------------------------------------------------------
# JSON → Item リスト変換
# ---------------------------------------------------------------------------

def _load_items_from_json(json_path: str) -> List[Item]:
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    items: List[Item] = []
    for d in data:
        targets = [AvatarRef(code=t['code'], name=t['name']) for t in d.get('targets', [])]
        files = [FileAsset(filename=f['filename']) for f in d.get('files', [])]
        
        category_raw = d.get("category", "other")
        try:
            category = ItemCategory(category_raw)
        except ValueError:
            category = ItemCategory.OTHER

        items.append(Item(
            item_id=str(d.get("item_id", "0")),
            source=d.get("source", "booth"),
            source_url=d.get("source_url", d.get("url", "")),
            title=d.get("title", d.get("name", "")),
            description=d.get("description", d.get("description_excerpt", "")),
            thumbnail_url=d.get("thumbnail_url", d.get("image_url", "")),
            creator_id=d.get("creator_id", "unknown"),
            creator_name=d.get("creator_name", d.get("shop_name", "Unknown Shop")),
            published_at=datetime.fromisoformat(d['published_at']) if d.get('published_at') else None,
            tags_raw=d.get("tags_raw", d.get("tags", [])),
            tags_generated=d.get("tags_generated", []),
            category=category,
            like_count=d.get("like_count", 0),
            price=d.get("price", d.get("current_price"))
        ))

    return items


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="BoothItemManager2定量監査エンジン")
    p.add_argument("--catalog", required=True, help="catalog.jsonパス (data/structured/catalog.json)")
    # CrawlStats
    p.add_argument("--source-items", type=int, default=None,
                   help="クロール元アイテム総数（未知なら省略）")
    p.add_argument("--indexed-items", type=int, default=None,
                   help="インデックス済みアイテム数（省略時はJSON行数）")
    # FilterEvidence
    p.add_argument("--year-filter", type=int, default=None)
    p.add_argument("--popularity-filter", type=int, default=None)
    p.add_argument("--category-filter", type=int, default=None)
    # FeatureStats
    p.add_argument("--color-search", type=int, default=None)
    p.add_argument("--style-search", type=int, default=None)
    p.add_argument("--avatar-reverse-search", type=int, default=None)
    p.add_argument("--cross-category-search", type=int, default=None)
    return p.parse_args()


def main() -> None:
    args = _parse_args()

    items = _load_items_from_json(args.catalog)

    crawl = CrawlStats(
        source_items=args.source_items,
        indexed_items=args.indexed_items if args.indexed_items is not None else len(items),
    )
    filters = FilterEvidence(
        year_filter_count=args.year_filter,
        popularity_filter_count=args.popularity_filter,
        category_filter_count=args.category_filter,
    )
    features = FeatureStats(
        color_search=args.color_search,
        style_search=args.style_search,
        avatar_reverse_search=args.avatar_reverse_search,
        cross_category_search=args.cross_category_search,
    )

    report = QuantitativeAuditor().run(items, crawl, filters, features)
    print(format_report(report))


if __name__ == "__main__":
    main()
