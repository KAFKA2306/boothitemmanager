#!/usr/bin/env python3
"""Build the public catalogue HTML with the 2026 UI enhancement layer."""

from __future__ import annotations

import argparse
from pathlib import Path

CSS_MARKER = '<link rel="stylesheet" href="comparison.css">'
JS_MARKER = '<script src="comparison.js"></script>'


def build(source: Path, destination: Path) -> None:
    html = source.read_text(encoding="utf-8")
    if CSS_MARKER not in html:
        if "</head>" not in html:
            raise ValueError("index.html has no closing head element")
        html = html.replace("</head>", f"    {CSS_MARKER}\n</head>", 1)
    if JS_MARKER not in html:
        if "</body>" not in html:
            raise ValueError("index.html has no closing body element")
        html = html.replace("</body>", f"    {JS_MARKER}\n</body>", 1)

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

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(html, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path("index.html"))
    parser.add_argument("--output", type=Path, default=Path("dist/index.html"))
    args = parser.parse_args()
    build(args.source, args.output)
    print(f"Built enhanced catalogue: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
