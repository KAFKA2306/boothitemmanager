from __future__ import annotations

from pathlib import Path

from scripts.build_ui import build

ROOT = Path(__file__).resolve().parents[1]


def test_build_injects_comparison_assets(tmp_path: Path) -> None:
    output = tmp_path / "index.html"
    build(ROOT / "index.html", output)
    html = output.read_text(encoding="utf-8")

    assert '<link rel="stylesheet" href="comparison.css">' in html
    assert '<script src="comparison.js"></script>' in html
    assert html.index('comparison.css') < html.index('</head>')
    assert html.index('comparison.js') < html.index('</body>')
    assert html.count('comparison.css') == 1
    assert html.count('comparison.js') == 1


def test_comparison_script_has_url_provenance_and_comparison_contracts() -> None:
    script = (ROOT / "comparison.js").read_text(encoding="utf-8")
    for marker in (
        "const MAX_COMPARE = 4",
        "new URLSearchParams(location.search)",
        "history.replaceState",
        "params.set('compare'",
        "params.set('limit'",
        "function provenance(item)",
        "function enhanceCards()",
        "function showComparison()",
        "function addMobileFilterUi()",
        "function renderActiveSummary()",
        "function restoreUrlState()",
        "data-compare-item",
        "販売ページ観測",
        "正規化タグ",
        "派生分類",
        "対応不明",
    ):
        assert marker in script


def test_comparison_css_removes_double_scroll_and_supports_mobile() -> None:
    css = (ROOT / "comparison.css").read_text(encoding="utf-8")
    for marker in (
        "height: auto !important",
        "overflow: visible !important",
        ".ux-filter-open",
        ".ux-compare-tray",
        ".ux-comparison-panel",
        ".asset-provenance",
        ".provenance-observed",
        ".provenance-normalized",
        ".provenance-derived",
        ".provenance-unknown",
        "min-height: 44px",
        "@media (max-width: 800px)",
        "@media (prefers-reduced-motion: reduce)",
    ):
        assert marker in css
