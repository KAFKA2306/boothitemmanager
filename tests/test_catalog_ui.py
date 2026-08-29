from __future__ import annotations

import importlib.util
import xml.etree.ElementTree as ET
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
    assert '<link rel="stylesheet" href="catalog-evidence.css">' in html
    assert '<script src="catalog-ux.js"></script>' in html
    assert '<script src="catalog-evidence.js"></script>' in html
    assert "comparison.css" not in html
    assert "comparison.js" not in html
    assert html.count("catalog-ux.css") == 1
    assert html.count("catalog-ux.js") == 1
    assert html.count("catalog-evidence.css") == 1
    assert html.count("catalog-evidence.js") == 1


def test_build_enforces_kafka_palette_and_cascade(tmp_path: Path) -> None:
    output = tmp_path / "index.html"
    build(ROOT / "index.html", output)
    html = output.read_text(encoding="utf-8")
    lower = html.lower()

    for forbidden in (
        "#00f0ff",
        "#ff007a",
        "#9d00ff",
        "rgba(0, 240, 255",
        "rgba(255, 0, 122",
    ):
        assert forbidden not in lower
    assert '<meta name="theme-color" content="#F6F7FB">' in html
    assert "--accent: var(--ks-blue)" in html
    assert html.rfind("kafka-signal.css") > html.rfind("</style>")


def test_kafka_theme_is_single_palette_contract() -> None:
    css = (ROOT / "kafka-signal.css").read_text(encoding="utf-8")
    for token in ("#F6F7FB", "#39445A", "#8D97AA", "#9CC8EB", "#C9B9E8", "#EBC5CF"):
        assert token in css
    for forbidden in ("#00f0ff", "#ff007a", "#9d00ff"):
        assert forbidden not in css.lower()
    assert ".logo-icon" in css and "box-shadow: none !important" in css
    assert ":focus-visible" in css
    assert "prefers-reduced-motion" in css


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


def test_compatibility_evidence_is_explicit_non_inferential_and_shareable() -> None:
    script = (ROOT / "catalog-evidence.js").read_text(encoding="utf-8")
    css = (ROOT / "catalog-evidence.css").read_text(encoding="utf-8")

    for marker in (
        "function renderCompatibilityEvidence(item)",
        "販売ページ記載から抽出",
        "不明 — このデータから販売者明示の対応先を確認できません。",
        "検索・分類用であり、互換性の根拠ではありません。",
        "BOOTHで最新情報を確認",
        "購入・導入前の最終判断",
        "last_observed_at || item?.last_changed_at",
        "#item-${encodeURIComponent(String(id))}",
        "function restoreSharedItem()",
    ):
        assert marker in script
    assert "対応保証" not in script
    assert "provenance" not in script
    assert "params.set('item'" not in script
    assert ".compatibility-evidence" in css
    assert "@media (max-width: 520px)" in css


def test_avatar_filter_uses_compatibility_targets_not_general_tags() -> None:
    script = (ROOT / "catalog-ux.js").read_text(encoding="utf-8")
    start = script.index("function matchesSelectedAvatar(item)")
    end = script.index("\n  function addSkipLink()", start)
    helper = script[start:end]

    assert "item.compatible_avatars || item.targets || []" in helper
    assert "item.tags" not in helper
    assert "filtered.filter(matchesSelectedAvatar)" in script


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


def test_public_search_metadata_uses_cloudflare_production() -> None:
    production = "https://boothitemmanager.pages.dev/"
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    robots = (ROOT / "robots.txt").read_text(encoding="utf-8")
    sitemap = ET.parse(ROOT / "sitemap.xml")

    assert readme.splitlines()[0] == production
    assert f'<link rel="canonical" href="{production}">' in html
    assert f"Sitemap: {production}sitemap.xml" in robots

    namespace = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    locations = [node.text for node in sitemap.findall("s:url/s:loc", namespace)]
    assert locations == [production, f"{production}ai-tools.html"]
    assert all(location.startswith(production) for location in locations)


def test_task_build_uses_single_canonical_build_path() -> None:
    taskfile = (ROOT / "Taskfile.yml").read_text(encoding="utf-8")
    build_section = taskfile.split("  refresh:", 1)[0]

    assert "bash build_static.sh" in build_section
    assert "api/*.js" not in build_section
    assert "|| true" not in build_section


def test_repository_has_no_javascript_catalog_fallback_assets() -> None:
    assert not (ROOT / "api" / "metadata.js").exists()
    assert list((ROOT / "api").glob("catalog_summary_part*.js")) == []
