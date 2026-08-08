#!/usr/bin/env python3
"""Build the public catalogue HTML with the retained UI assets."""

from __future__ import annotations

import argparse
from pathlib import Path

CSS_MARKERS = (
    '<link rel="stylesheet" href="kafka-signal.css">',
)
JS_MARKERS = (
    '<script src="kafka-signal.js"></script>',
)
META_MARKER = '<meta name="kafka-signal-release" content="kafka-signal-v1.0.0">'


def build(source: Path, destination: Path) -> None:
    html = source.read_text(encoding="utf-8")
    if "</head>" not in html:
        raise ValueError("index.html has no closing head element")
    if "</body>" not in html:
        raise ValueError("index.html has no closing body element")
    for marker in CSS_MARKERS:
        if marker not in html:
            html = html.replace("</head>", f"    {marker}\n</head>", 1)
    if META_MARKER not in html:
        html = html.replace("</head>", f"    {META_MARKER}\n</head>", 1)
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
