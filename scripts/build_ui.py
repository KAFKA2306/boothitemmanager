#!/usr/bin/env python3
"""Build the public catalogue HTML and enforce the shared KAFKA theme contract."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

CSS_MARKERS = (
    '<link rel="stylesheet" href="catalog-ux.css">',
    '<link rel="stylesheet" href="kafka-signal.css">',
    '<link rel="stylesheet" href="catalog-evidence.css">',
)
JS_MARKERS = (
    '<script src="catalog-ux.js"></script>',
    '<script src="kafka-signal.js"></script>',
    '<script src="catalog-evidence.js"></script>',
)
META_MARKER = '<meta name="kafka-signal-release" content="kafka-signal-v2.0.0">'
THEME_META = '<meta name="theme-color" content="#F6F7FB">'
FORBIDDEN_NEON = (
    "#00f0ff",
    "#ff007a",
    "#9d00ff",
    "rgba(0, 240, 255",
    "rgba(255, 0, 122",
)

LEGACY_ROOT = re.compile(
    r"(?s):root\s*\{\s*"
    r"--accent:\s*#00f0ff;.*?"
    r"--font-heading:\s*'Outfit',\s*sans-serif;\s*\}"
)

THEME_ALIASES = """:root {
            --accent: var(--ks-blue);
            --accent-pink: var(--ks-pink);
            --accent-purple: var(--ks-lilac);
            --accent-glow: rgb(156 200 235 / 0.16);
            --pink-glow: rgb(235 197 207 / 0.16);
            --bg-dark: var(--ks-canvas);
            --bg-card: rgb(255 255 255 / 0.72);
            --border-color: rgb(57 68 90 / 0.10);
            --border-hover: rgb(156 200 235 / 0.72);
            --text-primary: var(--ks-ink);
            --text-secondary: var(--ks-muted-strong);
            --text-muted: var(--ks-muted);
            --font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            --font-heading: 'Outfit', sans-serif;
        }"""


def _normalize_legacy_theme(html: str) -> str:
    html, count = LEGACY_ROOT.subn(THEME_ALIASES, html, count=1)
    if count != 1:
        raise ValueError("legacy catalogue theme block changed; refusing an unreviewed build")
    html = html.replace("12121a/00f0ff/", "F6F7FB/39445A/")
    html = html.replace("#00f0ff", "var(--ks-blue)")
    html = html.replace("#ff007a", "var(--ks-pink)")
    html = html.replace("#9d00ff", "var(--ks-lilac)")
    html = re.sub(
        r"rgba\(\s*0\s*,\s*240\s*,\s*255\s*,\s*([0-9.]+)\s*\)",
        r"rgb(156 200 235 / \1)",
        html,
    )
    html = re.sub(
        r"rgba\(\s*255\s*,\s*0\s*,\s*122\s*,\s*([0-9.]+)\s*\)",
        r"rgb(235 197 207 / \1)",
        html,
    )
    return html


def build(source: Path, destination: Path) -> None:
    html = source.read_text(encoding="utf-8")
    if "</head>" not in html:
        raise ValueError("index.html has no closing head element")
    if "</body>" not in html:
        raise ValueError("index.html has no closing body element")

    html = _normalize_legacy_theme(html)

    for marker in CSS_MARKERS:
        if marker not in html:
            html = html.replace("</head>", f"    {marker}\n</head>", 1)
    if META_MARKER not in html:
        html = html.replace("</head>", f"    {META_MARKER}\n</head>", 1)
    if THEME_META not in html:
        html = html.replace("</head>", f"    {THEME_META}\n</head>", 1)
    for marker in JS_MARKERS:
        if marker not in html:
            html = html.replace("</body>", f"    {marker}\n</body>", 1)

    required_runtime_markers = (
        'id="search-bar"',
        'id="asset-grid"',
        'id="detail-dialog"',
        "function renderGrid()",
        "function renderStaticFilters()",
        "function fillModal(d)",
        "init();",
    )
    missing = [marker for marker in required_runtime_markers if marker not in html]
    if missing:
        raise ValueError("existing catalogue runtime changed: " + ", ".join(missing))

    lower = html.lower()
    leaked = [token for token in FORBIDDEN_NEON if token in lower]
    if leaked:
        raise ValueError(
            "forbidden legacy neon tokens remain in distribution: " + ", ".join(leaked)
        )

    if html.rfind("kafka-signal.css") < html.rfind("</style>"):
        raise ValueError("kafka-signal.css must be loaded after the inline legacy stylesheet")

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(html, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path("index.html"))
    parser.add_argument("--output", type=Path, default=Path("dist/index.html"))
    args = parser.parse_args()
    build(args.source, args.output)
    print(f"Built catalogue: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
