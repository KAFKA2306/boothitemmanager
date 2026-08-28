from scripts.build_seller_market_report import build_report, percentile


def test_percentile_interpolates_without_external_dependency():
    assert percentile([100, 200, 300, 400], 0.5) == 250
    assert percentile([100], 0.25) == 100
    assert percentile([], 0.5) is None


def test_report_separates_observed_and_derived_fields():
    items = [
        {
            "creator_id": "shop-a",
            "creator_name": "Shop A",
            "source_url": "https://booth.pm/ja/items/1",
            "price": 1000,
            "category": "OUTFIT",
            "last_observed_at": "2026-08-28T00:00:00Z",
            "targets": [{"code": "Kikyo", "name": "桔梗"}],
            "tag_set": {"style": ["Cute"], "color": ["Black"], "feature": ["ModularAvatar"]},
        },
        {
            "creator_id": "shop-a",
            "creator_name": "Shop A",
            "source_url": "https://booth.pm/ja/items/2",
            "price": 3000,
            "category": "OUTFIT",
            "last_observed_at": "2026-08-29T00:00:00Z",
            "targets": [{"code": "Kikyo", "name": "桔梗"}],
            "tag_set": {"style": ["Cute"], "color": ["White"], "feature": []},
        },
        {
            "creator_id": "shop-b",
            "creator_name": "Shop B",
            "source_url": "https://booth.pm/ja/items/3",
            "price": 5000,
            "category": "OUTFIT",
            "last_observed_at": "2026-08-29T01:00:00Z",
            "targets": [],
            "tag_set": {},
        },
    ]

    report = build_report(items)
    seller = next(row for row in report["sellers"] if row["seller_id"] == "shop-a")

    assert report["as_of"] == "2026-08-29T01:00:00Z"
    assert seller["item_count"] == 2
    assert seller["price"]["median"] == 2000
    assert seller["categories"][0]["market"]["median"] == 3000
    assert seller["explicit_avatar_counts"] == [{"name": "桔梗", "count": 2}]
    assert seller["derived"]["style"] == [{"name": "Cute", "count": 2}]
    assert "需要" in report["evidence_contract"]["not_measured"]
