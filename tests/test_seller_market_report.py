import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "scripts" / "build_seller_market_report.py"
PAGE_PATH = Path(__file__).parents[1] / "seller" / "market-report" / "index.html"
SPEC = importlib.util.spec_from_file_location("build_seller_market_report", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
build_report = MODULE.build_report
percentile = MODULE.percentile


def test_percentile_interpolates_without_external_dependency():
    assert percentile([100, 200, 300, 400], 0.5) == 250
    assert percentile([100], 0.25) == 100
    assert percentile([], 0.5) is None


def test_report_separates_observed_and_derived_fields_and_rejects_unverified_rows():
    items = [
        {
            "item_id": "1",
            "creator_id": "shop-a",
            "creator_name": "Shop A",
            "title": "Outfit A1",
            "source_url": "https://booth.pm/ja/items/1",
            "price": 1000,
            "category": "OUTFIT",
            "source_status": "observed",
            "last_observed_at": "2026-08-28T00:00:00Z",
            "targets": [{"code": "Kikyo", "name": "桔梗"}],
            "tag_set": {"style": ["Cute"], "color": ["Black"], "feature": ["ModularAvatar"]},
            "similar_items": ["3", "2", "5"],
        },
        {
            "item_id": "2",
            "creator_id": "shop-a",
            "creator_name": "Shop A",
            "title": "Outfit A2",
            "source_url": "https://booth.pm/ja/items/2",
            "price": 3000,
            "category": "OUTFIT",
            "source_status": "observed",
            "last_observed_at": "2026-08-29T00:00:00Z",
            "targets": [{"code": "Kikyo", "name": "桔梗"}],
            "tag_set": {"style": ["Cute"], "color": ["White"], "feature": []},
            "similar_items": ["3"],
        },
        {
            "item_id": "3",
            "creator_id": "shop-b",
            "creator_name": "Shop B",
            "title": "Comparable Outfit",
            "source_url": "https://booth.pm/ja/items/3",
            "price": 5000,
            "category": "OUTFIT",
            "source_status": "observed",
            "last_observed_at": "2026-08-29T01:00:00Z",
            "targets": [],
            "tag_set": {},
            "similar_items": ["1"],
        },
        {
            "item_id": "4",
            "creator_id": "unknown",
            "creator_name": "Unknown Shop",
            "title": "Unknown",
            "source_url": "https://booth.pm/ja/items/4",
            "price": 100,
            "category": "ASSET",
            "source_status": "observed",
            "last_observed_at": "2026-08-29T02:00:00Z",
            "targets": [],
            "tag_set": {},
            "similar_items": [],
        },
        {
            "item_id": "5",
            "creator_id": "shop-c",
            "creator_name": "Shop C",
            "title": "Old unverified price",
            "source_url": "https://booth.pm/ja/items/5",
            "price": 99999,
            "category": "OUTFIT",
            "audit_status": "UNVERIFIED",
            "targets": [],
            "tag_set": {},
            "similar_items": ["1"],
        },
    ]

    report = build_report(items)
    seller = next(row for row in report["sellers"] if row["seller_id"] == "shop-a")

    assert report["as_of"] == "2026-08-29T01:00:00Z"
    assert report["seller_count"] == 2
    assert report["included_item_count"] == 3
    assert report["excluded_item_count"] == 2
    assert report["excluded_reasons"] == {
        "observation_unverified": 1,
        "seller_unknown": 1,
    }
    assert all(row["seller_id"] not in {"unknown", "shop-c"} for row in report["sellers"])
    assert "ASSET" not in report["market_by_category"]
    assert report["market_by_category"]["OUTFIT"]["median"] == 3000
    assert seller["item_count"] == 2
    assert seller["item_ids"] == ["1", "2"]
    assert seller["price"]["median"] == 2000
    assert seller["categories"][0]["market"]["median"] == 3000
    assert seller["explicit_avatar_counts"] == [{"name": "桔梗", "count": 2}]
    assert seller["derived"]["style"] == [{"name": "Cute", "count": 2}]
    assert seller["comparable_items"] == [
        {
            "item_id": "3",
            "title": "Comparable Outfit",
            "seller_id": "shop-b",
            "seller_name": "Shop B",
            "category": "OUTFIT",
            "price": 5000,
            "source_url": "https://booth.pm/ja/items/3",
            "similarity_reference_count": 2,
        }
    ]
    assert "需要" in report["evidence_contract"]["not_measured"]
    assert "source_status=observed" in report["evidence_contract"]["inclusion"]
    assert "similar_items" in report["evidence_contract"]["comparable_items"]


def test_seller_page_accepts_booth_item_url_without_guessing_shop_identity():
    page = PAGE_PATH.read_text(encoding="utf-8")

    assert "BOOTH商品URL、販売者名、販売者ID" in page
    assert "booth\\.pm" in page
    assert "item_ids || []" in page
    assert "includes(itemId)" in page
    assert "収録済みのBOOTH商品URL" in page


def test_selected_seller_is_carried_into_business_inquiry_purposes():
    page = PAGE_PATH.read_text(encoding="utf-8")

    assert 'id="business-inquiry"' in page
    assert 'id="new-product-inquiry"' in page
    assert 'id="monthly-report-inquiry"' in page
    assert "template: 'seller-analysis.yml'" in page
    assert "ショップ全体の分析相談" in page
    assert "新商品企画の分析相談" in page
    assert "月次レポートの相談" in page
    assert "issues/new?${params.toString()}" in page


def test_market_report_renders_comparable_items_from_existing_similarity_data():
    page = PAGE_PATH.read_text(encoding="utf-8")

    assert 'id="comparable-body"' in page
    assert "seller.comparable_items || []" in page
    assert "row.source_url" in page
    assert "row.similarity_reference_count" in page


def test_report_restore_waits_for_data_once_and_share_failures_are_visible():
    page = PAGE_PATH.read_text(encoding="utf-8")

    assert "setInterval" not in page
    assert "if (initialSeller) showSellerReport(initialSeller);" in page
    assert 'id="share-report"' in page
    assert "navigator.share" in page
    assert "navigator.clipboard?.writeText" in page
    assert "共有できません" in page
    assert "URLをコピーできません" in page
