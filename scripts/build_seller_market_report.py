#!/usr/bin/env python3
"""Build compact seller-side market summaries from the checked-in BOOTH catalogue."""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

DERIVED_TAG_FIELDS = ("style", "color", "feature")


def percentile(values: list[int | float], probability: float) -> float | None:
    if not values:
        return None
    ordered = sorted(float(value) for value in values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def price_summary(values: list[int | float]) -> dict[str, int | float | None]:
    return {
        "count": len(values),
        "q1": percentile(values, 0.25),
        "median": percentile(values, 0.5),
        "q3": percentile(values, 0.75),
    }


def _counter_top(counter: Counter[str], limit: int = 20) -> list[dict[str, Any]]:
    return [
        {"name": name, "count": count}
        for name, count in sorted(counter.items(), key=lambda row: (-row[1], row[0]))[:limit]
    ]


def build_report(items: list[dict[str, Any]]) -> dict[str, Any]:
    sellers: dict[str, dict[str, Any]] = {}
    market_prices: defaultdict[str, list[float]] = defaultdict(list)
    as_of_values: list[str] = []

    for item in items:
        seller_id = str(item.get("creator_id") or "").strip()
        seller_name = str(item.get("creator_name") or "").strip()
        category = str(item.get("category") or "UNKNOWN").strip() or "UNKNOWN"
        price = item.get("price")
        if not seller_id or not seller_name or not isinstance(price, (int, float)) or price < 0:
            continue

        observed_at = item.get("last_observed_at")
        if isinstance(observed_at, str) and observed_at:
            as_of_values.append(observed_at)

        market_prices[category].append(float(price))
        seller = sellers.setdefault(
            seller_id,
            {
                "seller_id": seller_id,
                "seller_name": seller_name,
                "prices": [],
                "categories": defaultdict(list),
                "avatars": Counter(),
                "style": Counter(),
                "color": Counter(),
                "feature": Counter(),
                "source_urls": set(),
                "observed_at": [],
            },
        )
        seller["prices"].append(float(price))
        seller["categories"][category].append(float(price))
        seller["source_urls"].add(str(item.get("source_url") or ""))
        if isinstance(observed_at, str) and observed_at:
            seller["observed_at"].append(observed_at)

        for target in item.get("targets") or []:
            if isinstance(target, dict):
                name = str(target.get("name") or target.get("code") or "").strip()
                if name:
                    seller["avatars"][name] += 1

        tag_set = item.get("tag_set") or {}
        if isinstance(tag_set, dict):
            for field in DERIVED_TAG_FIELDS:
                for value in tag_set.get(field) or []:
                    name = str(value).strip()
                    if name:
                        seller[field][name] += 1

    market = {
        category: price_summary(prices)
        for category, prices in sorted(market_prices.items())
    }
    seller_rows = []
    for seller in sellers.values():
        category_rows = []
        for category, prices in sorted(seller["categories"].items()):
            category_rows.append(
                {
                    "category": category,
                    "seller": price_summary(prices),
                    "market": market[category],
                }
            )
        seller_rows.append(
            {
                "seller_id": seller["seller_id"],
                "seller_name": seller["seller_name"],
                "item_count": len(seller["prices"]),
                "as_of": max(seller["observed_at"]) if seller["observed_at"] else None,
                "price": price_summary(seller["prices"]),
                "categories": category_rows,
                "explicit_avatar_counts": _counter_top(seller["avatars"]),
                "derived": {
                    field: _counter_top(seller[field]) for field in DERIVED_TAG_FIELDS
                },
            }
        )

    seller_rows.sort(key=lambda row: (-row["item_count"], row["seller_name"], row["seller_id"]))
    return {
        "schema_version": 1,
        "as_of": max(as_of_values) if as_of_values else None,
        "source": "api/details/shard_*.json",
        "evidence_contract": {
            "seller_and_price": "BOOTH観測値",
            "explicit_avatar_counts": "販売ページ由来の対応情報を正規化した値",
            "derived": "検索用に導出したタグ。販売者の明示事実とは別扱い",
            "not_measured": ["需要", "売上", "購入率"],
        },
        "market_by_category": market,
        "seller_count": len(seller_rows),
        "sellers": seller_rows,
    }


def load_items(api_dir: Path) -> list[dict[str, Any]]:
    detail_dir = api_dir / "details"
    shards = sorted(detail_dir.glob("shard_*.json"))
    if not shards:
        raise FileNotFoundError(f"detail shards not found: {detail_dir}")
    items: list[dict[str, Any]] = []
    for shard in shards:
        payload = json.loads(shard.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"detail shard must be an object: {shard}")
        items.extend(value for value in payload.values() if isinstance(value, dict))
    return items


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-dir", type=Path, default=Path("api"))
    parser.add_argument("--output", type=Path, default=Path("dist/api/seller_market_report.json"))
    args = parser.parse_args()

    report = build_report(load_items(args.api_dir))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    print(
        f"Built seller market report: {report['seller_count']} sellers, as_of={report['as_of']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
