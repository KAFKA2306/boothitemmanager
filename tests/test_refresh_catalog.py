from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "refresh_catalog", ROOT / "scripts" / "refresh_catalog.py"
)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


def product_html(
    item_id: str,
    *,
    title: str = "Example",
    price: int = 1200,
    availability: str = "https://schema.org/InStock",
) -> str:
    return f'''<!doctype html><html><head>
<meta property="og:title" content="{title}">
<meta property="og:image" content="https://example.invalid/{item_id}.jpg">
<meta name="description" content="seller description">
<script type="application/ld+json">{{"@type":"Product","name":"{title}","offers":{{"price":"{price}","availability":"{availability}"}}}}</script>
</head><body></body></html>'''


def test_discover_item_urls_deduplicates_and_normalizes() -> None:
    html = '''<a href="/ja/items/123">a</a><a href="https://booth.pm/ja/items/123?x=1">b</a><a href="/ja/items/456">c</a>'''
    assert MOD.discover_item_urls(html) == {
        "123": "https://booth.pm/ja/items/123",
        "456": "https://booth.pm/ja/items/456",
    }


def test_parse_item_page_uses_observed_product_fields() -> None:
    obs = MOD.parse_item_page("123", "https://booth.pm/ja/items/123", product_html("123"))
    assert obs.status_code == 200
    assert obs.title == "Example"
    assert obs.price == 1200
    assert obs.thumbnail.endswith("/123.jpg")
    assert obs.description == "seller description"


def test_update_summary_is_noop_when_material_fields_match() -> None:
    row = {
        "id": "123",
        "title": "Example",
        "price": 1200,
        "thumbnail": "https://example.invalid/123.jpg",
        "availability": "https://schema.org/InStock",
        "source_status": "observed",
    }
    obs = MOD.parse_item_page("123", "https://booth.pm/ja/items/123", product_html("123"))
    assert MOD.update_summary(row, obs, "2026-08-21T00:00:00Z") is False
    assert "last_observed_at" not in row


def test_update_summary_records_material_change_only() -> None:
    row = {
        "id": "123",
        "title": "Old",
        "price": 1200,
        "thumbnail": "https://example.invalid/123.jpg",
        "source_status": "observed",
    }
    obs = MOD.parse_item_page(
        "123", "https://booth.pm/ja/items/123", product_html("123", title="New")
    )
    assert MOD.update_summary(row, obs, "2026-08-21T00:00:00Z") is True
    assert row["title"] == "New"
    assert row["last_observed_at"] == "2026-08-21T00:00:00Z"
    assert row["last_changed_at"] == "2026-08-21T00:00:00Z"


def test_new_item_is_conservative_asset_without_invented_compatibility() -> None:
    obs = MOD.parse_item_page("999", "https://booth.pm/ja/items/999", product_html("999"))
    row = MOD.summary_for_new(obs, "2026-08-21T00:00:00Z")
    assert row["category"] == "ASSET"
    assert row["compatible_avatars"] == []
    assert row["tags"] == []
    assert row["author"] == "Unknown Shop"
