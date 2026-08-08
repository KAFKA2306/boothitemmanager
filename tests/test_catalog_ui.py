from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD_UI_PATH = ROOT / "scripts" / "build_ui.py"
SPEC = importlib.util.spec_from_file_location("boothitemmanager_build_ui", BUILD_UI_PATH)
assert SPEC is not None and SPEC.loader is not None
BUILD_UI = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILD_UI)
build = BUILD_UI.build


def test_build_injects_catalog_assets_without_removed_controls(tmp_path: Path) -> None:
    output = tmp_path / "index.html"
    build(ROOT / "index.html", output)
    html = output.read_text(encoding="utf-8")

    assert '<link rel="stylesheet" href="catalog-ux.css">' in html
    assert '<script src="catalog-ux.js"></script>' in html
    assert "comparison.css" not in html
    assert "comparison.js" not in html
    assert html.count("catalog-ux.css") == 1
    assert html.count("catalog-ux.js") == 1


def test_catalog_script_keeps_neutral_ux_only() -> None:
    script = (ROOT / "catalog-ux.js").read_text(encoding="utf-8")
    for marker in (
        "function addMobileFilterUi()",
        "function enhanceCards()",
        "function renderActiveSummary()",
        "function restoreUrlState()",
        "new URLSearchParams(location.search)",
        "history.replaceState",
        "params.set('limit'",
    ):
        assert marker in script

    for removed in (
        "data-compare-item",
        "data-open-detail",
        "ux-compare-tray",
        "ux-comparison-panel",
        "provenance",
        "params.set('compare'",
        "params.set('item'",
    ):
        assert removed not in script


def test_catalog_css_keeps_responsive_ux_without_removed_ui() -> None:
    css = (ROOT / "catalog-ux.css").read_text(encoding="utf-8")
    for marker in (
        "height: auto !important",
        "overflow: visible !important",
        ".ux-filter-open",
        ".ux-results-summary",
        "min-height: 44px",
        "@media (max-width: 800px)",
        "@media (prefers-reduced-motion: reduce)",
    ):
        assert marker in css

    for removed in (
        ".ux-compare-tray",
        ".ux-comparison-panel",
        ".asset-provenance",
        ".ux-provenance-section",
        ".asset-compare",
    ):
        assert removed not in css


def test_why_shown_panel_is_not_generated_or_styled() -> None:
    script = (ROOT / "kafka-signal.js").read_text(encoding="utf-8")
    css = (ROOT / "kafka-signal.css").read_text(encoding="utf-8")

    assert "why-shown" not in script
    assert "この商品が表示された理由" not in script
    assert "現在の検索・カテゴリ・タグ条件に一致したため表示しています" not in script
    assert ".why-shown" not in css
