import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "scripts" / "build_market_opportunities.py"
SPEC = importlib.util.spec_from_file_location("build_market_opportunities", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

build_opportunities = MODULE.build_opportunities
render_issue = MODULE.render_issue


def item(
    item_id: str,
    *,
    category: str,
    avatar: str,
    price: int = 2000,
    observed: bool = True,
):
    return {
        "item_id": item_id,
        "creator_id": f"shop-{item_id}",
        "creator_name": f"Shop {item_id}",
        "title": f"Item {item_id}",
        "source_url": f"https://booth.pm/ja/items/{item_id}",
        "price": price,
        "category": category,
        "source_status": "observed" if observed else "unknown",
        "last_observed_at": "2026-10-08T00:00:00Z" if observed else None,
        "targets": [{"name": avatar}],
        "tag_set": {},
        "similar_items": [],
    }


def test_supply_gap_is_ranked_without_becoming_demand_claim():
    items = [
        item("1", category="OUTFIT", avatar="Avatar A", price=1000),
        item("2", category="OUTFIT", avatar="Avatar B", price=2000),
        item("3", category="OUTFIT", avatar="Avatar B", price=3000),
        item("4", category="OUTFIT", avatar="Avatar B", price=4000),
        item("5", category="OUTFIT", avatar="Avatar B", price=5000),
        item("6", category="OUTFIT", avatar="Avatar B", price=6000),
        item("7", category="ACCESSORY", avatar="Avatar A"),
        item("8", category="ACCESSORY", avatar="Avatar A"),
        item("9", category="ACCESSORY", avatar="Avatar A"),
        item("10", category="ACCESSORY", avatar="Avatar A"),
    ]

    report = build_opportunities(
        items,
        min_category_count=5,
        min_avatar_count=5,
        min_expected_count=2,
    )

    selected = report["selected_intent"]
    assert selected is not None
    assert selected["key"] == "OUTFIT:Avatar A"
    assert selected["evidence"]["pair_items"] == 1
    assert selected["evidence"]["expected_pair_items"] == 3.0
    assert selected["next_action"] == "validate_demand_before_prototype"
    assert "demand" in report["evidence_contract"]["not_measured"]
    assert "需要" in selected["falsification"]


def test_unverified_listing_is_excluded_from_market_intent():
    items = [
        item(str(index), category="OUTFIT", avatar="Avatar A")
        for index in range(1, 6)
    ]
    items.extend(
        item(str(index), category="OUTFIT", avatar="Avatar B")
        for index in range(6, 11)
    )
    items.append(
        item("11", category="OUTFIT", avatar="Avatar C", observed=False)
    )

    report = build_opportunities(
        items,
        min_category_count=5,
        min_avatar_count=1,
        min_expected_count=0.5,
    )

    assert report["eligible_item_count"] == 10
    assert all(
        row["avatar"] != "Avatar C"
        for row in report["opportunities"]
    )


def test_issue_keeps_hypothesis_and_falsification_together():
    items = [
        item("1", category="OUTFIT", avatar="Avatar A"),
        item("2", category="OUTFIT", avatar="Avatar B"),
        item("3", category="OUTFIT", avatar="Avatar B"),
        item("4", category="OUTFIT", avatar="Avatar B"),
        item("5", category="OUTFIT", avatar="Avatar B"),
        item("6", category="OUTFIT", avatar="Avatar B"),
        item("7", category="ACCESSORY", avatar="Avatar A"),
        item("8", category="ACCESSORY", avatar="Avatar A"),
        item("9", category="ACCESSORY", avatar="Avatar A"),
        item("10", category="ACCESSORY", avatar="Avatar A"),
    ]
    report = build_opportunities(
        items,
        min_category_count=5,
        min_avatar_count=5,
        min_expected_count=2,
    )

    body = render_issue(report)
    assert "<!-- autonomous-market-intent -->" in body
    assert "需要の証明ではありません" in body
    assert "validate_demand_before_prototype" in body
    assert "image2outfit" in body
