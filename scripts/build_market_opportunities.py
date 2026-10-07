#!/usr/bin/env python3
"""Derive evidence-bounded product opportunity hypotheses from the BOOTH catalogue.

This module intentionally measures supply gaps only. It must not present catalogue
sparsity as proof of demand, sales, conversion, or profitability.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from build_seller_market_report import _market_item_exclusion_reason, load_items

NOT_MEASURED = ["demand", "sales", "conversion", "profitability"]
ELIGIBLE_CATEGORIES = {"ACCESSORY", "GIMMICK_TOOL", "HAIRSTYLE", "OUTFIT", "TEXTURE"}


def _explicit_targets(item: dict[str, Any]) -> set[str]:
    result: set[str] = set()
    for target in item.get("targets") or []:
        if not isinstance(target, dict):
            continue
        name = str(target.get("name") or target.get("code") or "").strip()
        if name:
            result.add(name)
    return result


def _source_url(item: dict[str, Any]) -> str:
    return str(item.get("source_url") or "").strip()


def build_opportunities(
    items: list[dict[str, Any]],
    *,
    min_category_count: int = 5,
    min_avatar_count: int = 5,
    min_expected_count: float = 2.0,
    limit: int = 20,
) -> dict[str, Any]:
    eligible = [item for item in items if _market_item_exclusion_reason(item) is None]
    total = len(eligible)

    category_count: Counter[str] = Counter()
    avatar_count: Counter[str] = Counter()
    pair_count: Counter[tuple[str, str]] = Counter()
    category_prices: defaultdict[str, list[float]] = defaultdict(list)
    category_urls: defaultdict[str, list[str]] = defaultdict(list)
    avatar_urls: defaultdict[str, list[str]] = defaultdict(list)
    as_of: list[str] = []

    for item in eligible:
        category = str(item.get("category") or "UNKNOWN").strip() or "UNKNOWN"
        if category not in ELIGIBLE_CATEGORIES:
            continue
        category_count[category] += 1

        price = item.get("price")
        if isinstance(price, (int, float)):
            category_prices[category].append(float(price))

        url = _source_url(item)
        if url and url not in category_urls[category]:
            category_urls[category].append(url)

        observed_at = str(item.get("last_observed_at") or "").strip()
        if observed_at:
            as_of.append(observed_at)

        for avatar in _explicit_targets(item):
            avatar_count[avatar] += 1
            pair_count[(category, avatar)] += 1
            if url and url not in avatar_urls[avatar]:
                avatar_urls[avatar].append(url)

    opportunities: list[dict[str, Any]] = []
    if total:
        for category, c_count in category_count.items():
            if c_count < min_category_count:
                continue
            for avatar, a_count in avatar_count.items():
                if a_count < min_avatar_count:
                    continue

                expected = (c_count * a_count) / total
                if expected < min_expected_count:
                    continue

                observed = pair_count[(category, avatar)]
                gap = expected - observed
                if gap <= 0:
                    continue

                gap_ratio = gap / expected
                support = min(1.0, expected / 10.0)
                score = round(100.0 * gap_ratio * (0.6 + 0.4 * support), 1)
                pair_prices = [
                    float(item["price"])
                    for item in eligible
                    if str(item.get("category") or "").strip() == category
                    and avatar in _explicit_targets(item)
                    and isinstance(item.get("price"), (int, float))
                ]
                category_price = category_prices.get(category, [])

                opportunities.append(
                    {
                        "key": f"{category}:{avatar}",
                        "category": category,
                        "avatar": avatar,
                        "score": score,
                        "hypothesis": (
                            f"{avatar}向け{category}は、観測カタログ内のカテゴリ比率と"
                            "明示対応アバター比率から期待される供給件数より少ない。"
                            "新商品候補として需要検証する価値がある。"
                        ),
                        "evidence": {
                            "eligible_items": total,
                            "category_items": c_count,
                            "avatar_items": a_count,
                            "pair_items": observed,
                            "expected_pair_items": round(expected, 2),
                            "estimated_supply_gap": round(gap, 2),
                            "gap_ratio": round(gap_ratio, 4),
                            "category_price_median": (
                                median(category_price) if category_price else None
                            ),
                            "pair_price_median": median(pair_prices) if pair_prices else None,
                            "category_examples": category_urls[category][:3],
                            "avatar_examples": avatar_urls[avatar][:3],
                        },
                        "falsification": (
                            "この差は需要の証明ではない。検索需要、購入意向、既存商品の反応、"
                            "ユーザー要望など独立した需要シグナルで支持されなければ棄却する。"
                        ),
                        "next_action": "validate_demand_before_prototype",
                    }
                )

    opportunities.sort(
        key=lambda row: (
            -row["score"],
            -row["evidence"]["estimated_supply_gap"],
            row["category"],
            row["avatar"],
        )
    )
    opportunities = opportunities[: max(0, limit)]
    selected = opportunities[0] if opportunities else None

    return {
        "schema_version": 1,
        "as_of": max(as_of) if as_of else None,
        "source": "api/details/shard_*.json",
        "method": {
            "name": "catalog_supply_gap",
            "description": (
                "観測済み商品のカテゴリ比率と明示対応アバター比率から独立期待値を作り、"
                "実測供給が下回る組み合わせを商品機会仮説として順位付けする。"
            ),
            "minimum_category_items": min_category_count,
            "minimum_avatar_items": min_avatar_count,
            "minimum_expected_pair_items": min_expected_count,
            "eligible_categories": sorted(ELIGIBLE_CATEGORIES),
        },
        "evidence_contract": {
            "uses_only": [
                "source_status=observed",
                "last_observed_at",
                "category",
                "explicit avatar targets",
                "observed price",
            ],
            "not_measured": NOT_MEASURED,
            "claim_boundary": (
                "scoreは供給ギャップ仮説の優先度であり、需要・売上・収益性の予測ではない。"
            ),
        },
        "eligible_item_count": total,
        "opportunity_count": len(opportunities),
        "selected_intent": selected,
        "opportunities": opportunities,
    }


def render_issue(report: dict[str, Any]) -> str:
    selected = report.get("selected_intent")
    if not isinstance(selected, dict):
        return ""

    evidence = selected["evidence"]
    links = []
    for url in [
        *evidence.get("category_examples", []),
        *evidence.get("avatar_examples", []),
    ]:
        if url and url not in links:
            links.append(url)

    source_lines = "\n".join(f"- {url}" for url in links[:6]) or "- 参照URLなし"
    return f"""<!-- autonomous-market-intent -->
# 自律市場意図

**候補:** {selected['avatar']} × {selected['category']}
**優先度:** {selected['score']}

{selected['hypothesis']}

## 観測根拠

- 対象カタログ: {evidence['eligible_items']}件
- カテゴリ供給: {evidence['category_items']}件
- アバター明示対応: {evidence['avatar_items']}件
- 組み合わせ実測: {evidence['pair_items']}件
- 独立期待値: {evidence['expected_pair_items']}件
- 推定供給ギャップ: {evidence['estimated_supply_gap']}件
- カテゴリ価格中央値: {evidence['category_price_median']}
- 組み合わせ価格中央値: {evidence['pair_price_median']}

## 反証条件

{selected['falsification']}

このIssueは**需要の証明ではありません**。需要検証が通るまでは制作着手を確定しません。

## 次の状態

`validate_demand_before_prototype`

需要シグナルを追加確認し、支持された場合だけ image2outfit 側の制作候補へ渡す。

## 参照商品

{source_lines}

生成元: `scripts/build_market_opportunities.py`
観測時点: {report.get('as_of')}
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-dir", type=Path, default=Path("api"))
    parser.add_argument("--output", type=Path, default=Path("dist/api/market_opportunities.json"))
    parser.add_argument("--issue-output", type=Path)
    parser.add_argument("--min-category-count", type=int, default=5)
    parser.add_argument("--min-avatar-count", type=int, default=5)
    parser.add_argument("--min-expected-count", type=float, default=2.0)
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()

    report = build_opportunities(
        load_items(args.api_dir),
        min_category_count=args.min_category_count,
        min_avatar_count=args.min_avatar_count,
        min_expected_count=args.min_expected_count,
        limit=args.limit,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )

    if args.issue_output:
        args.issue_output.parent.mkdir(parents=True, exist_ok=True)
        args.issue_output.write_text(render_issue(report), encoding="utf-8")

    selected = report["selected_intent"]
    print(
        "Built market opportunities: "
        f"{report['opportunity_count']} candidates, "
        f"selected={selected['key'] if selected else 'none'}, "
        f"as_of={report['as_of']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
