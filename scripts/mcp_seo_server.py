#!/usr/bin/env python3
"""
Model Context Protocol (MCP) server for BoothItemManager2.
Exposes catalog summaries and SEO status to external AI clients.
Inspired by every-app/open-seo.
"""

import json
import os
import sys
from datetime import datetime
from typing import Any

import yaml

# Adjust sys.path to load local boothitemmanager2 module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from boothitemmanager2.quantitative_auditor import (
    CrawlStats,
    FeatureStats,
    FilterEvidence,
    QuantitativeAuditor,
)
from boothitemmanager2.storage import AvatarRef, Item, ItemCategory, TagSet

CATALOG_PATH = "data/structured/catalog.json"
AVATARS_PATH = "ontology/avatars.yaml"
TAGS_PATH = "ontology/tags.yaml"

# Global data store loaded on startup
ITEMS: list[Item] = []
ITEMS_DICT: dict[str, Item] = {}
AVATARS_ONTOLOGY: dict[str, Any] = {}
TAGS_ONTOLOGY: dict[str, Any] = {}


def log(message: str) -> None:
    """Print log message to stderr (so it doesn't corrupt stdout JSON-RPC channel)."""
    sys.stderr.write(f"[{datetime.now().isoformat()}] {message}\n")
    sys.stderr.flush()


def load_data() -> None:
    """Loads catalog data and ontology files into memory."""
    global ITEMS, ITEMS_DICT, AVATARS_ONTOLOGY, TAGS_ONTOLOGY

    # Load catalog.json
    if not os.path.exists(CATALOG_PATH):
        log(f"Error: Catalog file not found at {CATALOG_PATH}. Please run pipeline first.")
        sys.exit(1)

    log(f"Loading catalog from {CATALOG_PATH}...")
    with open(CATALOG_PATH, encoding="utf-8") as f:
        catalog_data = json.load(f)

    items_temp = []
    for data in catalog_data:
        ts_data = data.get("tag_set") or {}
        tag_set = TagSet(
            appearance=ts_data.get("appearance", []),
            body_type=ts_data.get("body_type", []),
            style=ts_data.get("style", []),
            color=ts_data.get("color", []),
            outfit_type=ts_data.get("outfit_type", []),
            accessory=ts_data.get("accessory", []),
            feature=ts_data.get("feature", []),
            platform=ts_data.get("platform", []),
            season=ts_data.get("season", []),
            avatar_link=ts_data.get("avatar_link", []),
            material_property=ts_data.get("material_property", []),
            niche_subculture=ts_data.get("niche_subculture", []),
            activity_scene=ts_data.get("activity_scene", []),
        )

        targets = []
        for t in data.get("targets", []):
            if isinstance(t, dict):
                targets.append(AvatarRef(code=t.get("code", ""), name=t.get("name", "")))
            elif isinstance(t, str):
                targets.append(AvatarRef(code=t, name=t))

        pub_at = None
        pub_str = data.get("published_at")
        if pub_str:
            try:
                pub_at = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
            except Exception:
                pass

        cat_str = data.get("category")
        category = (
            ItemCategory[cat_str] if cat_str in ItemCategory.__members__ else ItemCategory.ASSET
        )

        item = Item(
            item_id=str(data.get("item_id", "")),
            source_url=data.get("source_url", ""),
            title=data.get("title", ""),
            description=data.get("description", ""),
            thumbnail_url=data.get("thumbnail_url", ""),
            creator_id=data.get("creator_id", ""),
            creator_name=data.get("creator_name", ""),
            published_at=pub_at,
            like_count=data.get("like_count", 0),
            price=data.get("price"),
            category=category,
            tag_set=tag_set,
            similar_items=data.get("similar_items", []),
            user_state=data.get("user_state", {}),
            tags_raw=data.get("tags_raw", []),
            targets=targets,
            files=data.get("files", []),
            audit_status=data.get("audit_status", "UNVERIFIED"),
            trace_log=data.get("trace_log", {}),
            raw_html_snippet=data.get("raw_html_snippet"),
        )
        items_temp.append(item)
        ITEMS_DICT[item.item_id] = item

    ITEMS = items_temp
    log(f"Successfully loaded {len(ITEMS)} items into memory.")

    # Load ontology
    if os.path.exists(AVATARS_PATH):
        log(f"Loading avatars ontology from {AVATARS_PATH}...")
        with open(AVATARS_PATH, encoding="utf-8") as f:
            AVATARS_ONTOLOGY = yaml.safe_load(f) or {}
    else:
        log(f"Warning: Avatars ontology not found at {AVATARS_PATH}.")

    if os.path.exists(TAGS_PATH):
        log(f"Loading tags ontology from {TAGS_PATH}...")
        with open(TAGS_PATH, encoding="utf-8") as f:
            TAGS_ONTOLOGY = yaml.safe_load(f) or {}
    else:
        log(f"Warning: Tags ontology not found at {TAGS_PATH}.")


# SEO Auditor helper for single item
def evaluate_single_item_seo(item: Item) -> dict[str, Any]:
    """Evaluates SEO checklist for a single item."""
    issues: list[str] = []
    passed: list[str] = []

    # Title checks
    title_len = len(item.title)
    if title_len == 0:
        issues.append("Title is missing.")
    elif title_len < 10:
        issues.append(f"Title is too short ({title_len} chars). Target: >= 10 chars.")
    elif title_len > 80:
        issues.append(
            f"Title is very long ({title_len} chars), might get truncated in search results."
        )
    else:
        passed.append(f"Title length is optimal ({title_len} chars).")

    # Description checks
    desc_len = len(item.description) if item.description else 0
    if desc_len == 0:
        issues.append("Description is missing.")
    elif desc_len < 50:
        issues.append(f"Description is too short ({desc_len} chars). Target: >= 50 chars.")
    else:
        passed.append(f"Description length is optimal ({desc_len} chars).")

    # Thumbnail checks
    if not item.thumbnail_url:
        issues.append("Thumbnail image is missing.")
    else:
        passed.append("Thumbnail is present.")

    # Tags count
    tags_count = len(item.tags)
    if tags_count < 3:
        issues.append(f"Low tag count ({tags_count} tags). Target: >= 3 tags.")
    else:
        passed.append(f"Has sufficient tags ({tags_count} tags).")

    # Target Avatars checks
    if item.category in (
        ItemCategory.OUTFIT,
        ItemCategory.HAIRSTYLE,
        ItemCategory.ACCESSORY,
        ItemCategory.TEXTURE,
    ):
        if not item.targets:
            issues.append(f"Category is {item.category.value} but no target avatars are linked.")
        else:
            passed.append(f"Target avatars are linked ({len(item.targets)} avatars).")

    # Similar items checks
    if not item.similar_items:
        issues.append("No similar items linked. Reduces internal link graph strength.")
    else:
        passed.append("Similar items are linked.")

    # Category tags mismatch checks
    if item.category in (ItemCategory.ANIMATION, ItemCategory.GIMMICK_TOOL):
        mismatches = len(item.tag_set.outfit_type) + len(item.tag_set.accessory)
        if mismatches > 0:
            issues.append(
                f"Category is {item.category.value} but contains outfit or accessory tags."
            )

    status = "FAIL" if issues else "PASS"

    return {
        "item_id": item.item_id,
        "title": item.title,
        "category": item.category.value,
        "creator": item.creator_name,
        "status": status,
        "issues": issues,
        "passed_checks": passed,
    }


# Tool Handlers
def handle_get_catalog_summary(arguments: dict[str, Any]) -> str:
    """Returns general statistics of the catalog."""
    total = len(ITEMS)
    categories: dict[str, int] = {}
    total_tags = 0
    tag_counts: dict[str, int] = {}
    prices: list[int] = []
    likes: list[int] = []

    for item in ITEMS:
        cat = item.category.value
        categories[cat] = categories.get(cat, 0) + 1

        tags = item.tags
        total_tags += len(tags)
        for t in tags:
            tag_counts[t] = tag_counts.get(t, 0) + 1

        if item.price is not None:
            prices.append(item.price)

        if item.like_count is not None:
            likes.append(item.like_count)

    avg_price = sum(prices) / len(prices) if prices else 0.0
    max_price = max(prices) if prices else 0
    min_price = min(prices) if prices else 0
    avg_likes = sum(likes) / len(likes) if likes else 0.0
    max_likes = max(likes) if likes else 0
    avg_tags = total_tags / total if total > 0 else 0.0

    top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:20]

    summary = {
        "total_items": total,
        "categories_breakdown": categories,
        "price_stats": {
            "average_price": round(avg_price, 2),
            "max_price": max_price,
            "min_price": min_price,
            "items_with_price": len(prices),
        },
        "popularity_stats": {"average_likes": round(avg_likes, 2), "max_likes": max_likes},
        "tag_stats": {
            "average_tags_per_item": round(avg_tags, 2),
            "top_20_tags": {k: v for k, v in top_tags},
        },
    }
    return json.dumps(summary, ensure_ascii=False, indent=2)


def handle_get_seo_audit(arguments: dict[str, Any]) -> str:
    """Runs QuantitativeAuditor and returns a site-wide report."""
    color_search = sum(1 for i in ITEMS if i.tag_set.color)
    style_search = sum(1 for i in ITEMS if i.tag_set.style)
    avatar_rev_search = sum(1 for i in ITEMS if i.targets)
    cross_category_search = sum(1 for i in ITEMS if i.tag_set.outfit_type and i.tag_set.color)

    crawl_stats = CrawlStats(source_items=40317, indexed_items=len(ITEMS))

    filters = FilterEvidence(
        year_filter_count=sum(1 for i in ITEMS if i.published_at and i.published_at.year == 2026),
        popularity_filter_count=sum(1 for i in ITEMS if i.like_count and i.like_count > 100),
        category_filter_count=sum(1 for i in ITEMS if i.category != ItemCategory.ASSET),
    )

    features = FeatureStats(
        color_search=color_search,
        style_search=style_search,
        avatar_reverse_search=avatar_rev_search,
        cross_category_search=cross_category_search,
    )

    auditor = QuantitativeAuditor()
    report = auditor.run(ITEMS, crawl=crawl_stats, filters=filters, features=features)

    report_dict = {
        "total_items": report.total_items,
        "items_with_metadata": report.items_with_metadata,
        "items_with_tags": report.items_with_tags,
        "items_missing_fields": report.items_missing_fields,
        "coverage_rate": report.coverage_rate,
        "tagging_rate": report.tagging_rate,
        "missing_rate": report.missing_rate,
        "tagged_items": report.tagged_items,
        "invalid_tags": report.invalid_tags,
        "duplicate_tags": report.duplicate_tags,
        "multi_label_conflicts": report.multi_label_conflicts,
        "category_tag_mismatches": report.category_tag_mismatches,
        "valid_tag_rate": report.valid_tag_rate,
        "source_items": report.source_items,
        "indexed_items": report.indexed_items,
        "lost_items": report.lost_items,
        "sync_rate": report.sync_rate,
        "filter_constraints": {
            "year_filter": {
                "status": report.year_filter.status,
                "count": report.year_filter.evidence_count,
            },
            "popularity_filter": {
                "status": report.popularity_filter.status,
                "count": report.popularity_filter.evidence_count,
            },
            "category_filter": {
                "status": report.category_filter.status,
                "count": report.category_filter.evidence_count,
            },
        },
        "search_features": {
            "color_search_supported": report.color_search,
            "style_search_supported": report.style_search,
            "avatar_reverse_search_supported": report.avatar_reverse_search,
            "cross_category_search_supported": report.cross_category_search,
        },
        "feature_coverage_score": report.feature_coverage_score,
        "final_reliability_score": report.final_score,
    }

    return json.dumps(report_dict, ensure_ascii=False, indent=2)


def handle_inspect_item_seo(arguments: dict[str, Any]) -> str:
    """Checks the SEO details of a single item."""
    item_id = str(arguments.get("item_id", ""))
    if item_id not in ITEMS_DICT:
        raise ValueError(f"Item ID {item_id} not found in catalog.")

    item = ITEMS_DICT[item_id]
    result = evaluate_single_item_seo(item)
    return json.dumps(result, ensure_ascii=False, indent=2)


def handle_list_items_by_seo_status(arguments: dict[str, Any]) -> str:
    """Lists items matching SEO statuses or failure reasons."""
    status = arguments.get("status")
    issue = arguments.get("issue")
    limit = int(arguments.get("limit", 10))

    matched: list[dict[str, Any]] = []

    for item in ITEMS:
        if len(matched) >= limit:
            break

        eval_res = evaluate_single_item_seo(item)

        if status and eval_res["status"] != status:
            continue

        if issue:
            has_issue = False
            if issue == "missing_description" and (
                not item.description or len(item.description) < 10
            ):
                has_issue = True
            elif issue == "missing_targets" and not item.targets:
                has_issue = True
            elif issue == "low_tag_count" and len(item.tags) < 3:
                has_issue = True
            elif issue == "no_similar_items" and not item.similar_items:
                has_issue = True

            if not has_issue:
                continue

        matched.append(
            {
                "item_id": item.item_id,
                "title": item.title,
                "creator": item.creator_name,
                "category": item.category.value,
                "seo_status": eval_res["status"],
                "issues": eval_res["issues"],
            }
        )

    return json.dumps(matched, ensure_ascii=False, indent=2)


def handle_suggest_seo_optimizations(arguments: dict[str, Any]) -> str:
    """Suggests optimized titles, descriptions, and tags for an item."""
    item_id = str(arguments.get("item_id", ""))
    if item_id not in ITEMS_DICT:
        raise ValueError(f"Item ID {item_id} not found in catalog.")

    item = ITEMS_DICT[item_id]

    # 1. Title optimization
    import re

    cleaned_title = item.title
    brackets = re.findall(r"【[^】]+】|\[[^\]]+\]", cleaned_title)
    main_title = re.sub(r"【[^】]+】|\[[^\]]+\]", "", cleaned_title).strip()

    if not main_title:
        main_title = cleaned_title

    optimized_title = main_title
    if brackets:
        important_brackets = [
            b
            for b in brackets
            if any(kw in b for kw in ["PB", "PhysBone", "対応", "VRC", "Vroid", "3D"])
        ]
        if important_brackets:
            optimized_title = f"{main_title} " + " ".join(important_brackets)

    if len(optimized_title) > 60:
        optimized_title = optimized_title[:57] + "..."

    # 2. Suggested avatar targets based on text matching
    suggested_avatars: list[dict[str, str]] = []
    title_desc = f"{item.title} {item.description or ''}".lower()

    avatars_section = AVATARS_ONTOLOGY.get("avatars", {})
    for av_code, av_data in avatars_section.items():
        aliases = av_data.get("aliases", [av_code])
        canonical = av_data.get("canonical_name", av_code)

        for alias in aliases:
            if str(alias).lower() in title_desc:
                if not any(a["code"] == av_code for a in suggested_avatars):
                    suggested_avatars.append({"code": av_code, "name": canonical})
                break

    # 3. Suggested tags based on ontology tags/colors/styles
    suggested_tags: list[str] = []

    styles = TAGS_ONTOLOGY.get("styles", {})
    if not styles and os.path.exists("ontology/styles.yaml"):
        with open("ontology/styles.yaml", encoding="utf-8") as sf:
            styles_data = yaml.safe_load(sf) or {}
            styles = styles_data.get("styles", {})

    for style_name, style_data in styles.items():
        if isinstance(style_data, list):
            aliases = style_data
        elif isinstance(style_data, dict):
            aliases = style_data.get("aliases", [style_name])
        else:
            aliases = [style_name]
        for alias in aliases:
            if str(alias).lower() in title_desc and style_name not in item.tags:
                suggested_tags.append(style_name)
                break

    colors = TAGS_ONTOLOGY.get("Colors", {}) or TAGS_ONTOLOGY.get("colors", {})
    for color_name, color_data in colors.items():
        if isinstance(color_data, list):
            aliases = color_data
        elif isinstance(color_data, dict):
            aliases = color_data.get("aliases", [color_name])
        else:
            aliases = [color_name]
        for alias in aliases:
            if str(alias).lower() in title_desc and color_name not in item.tags:
                suggested_tags.append(color_name)
                break

    suggested_tags = list(set(suggested_tags))[:10]

    # 4. Description helper
    suggested_description = item.description
    if not suggested_description or len(suggested_description) < 50:
        target_names = [a["name"] for a in (suggested_avatars or [{"name": "VRChat Avatars"}])]
        suggested_description = (
            f"BOOTHで大人気の{item.creator_name}様作の3Dアイテム「{main_title}」です！\n"
            f"【対応アバター】: {', '.join(target_names)}\n"
            f"VRChatやその他メタバース空間でのご利用に最適化されています。"
        )

    suggestions = {
        "item_id": item.item_id,
        "original_title": item.title,
        "suggested_title": optimized_title,
        "original_tags": item.tags,
        "suggested_new_tags": suggested_tags,
        "original_targets": [{"code": t.code, "name": t.name} for t in item.targets],
        "suggested_new_targets": [
            a for a in suggested_avatars if a["code"] not in [t.code for t in item.targets]
        ],
        "suggested_description": suggested_description,
    }

    return json.dumps(suggestions, ensure_ascii=False, indent=2)


def get_markdown_audit_report() -> str:
    """Generates the audit report in a nice Markdown formatting."""
    color_search = sum(1 for i in ITEMS if i.tag_set.color)
    style_search = sum(1 for i in ITEMS if i.tag_set.style)
    avatar_rev_search = sum(1 for i in ITEMS if i.targets)
    cross_category_search = sum(1 for i in ITEMS if i.tag_set.outfit_type and i.tag_set.color)

    crawl_stats = CrawlStats(source_items=40317, indexed_items=len(ITEMS))
    filters = FilterEvidence(
        year_filter_count=sum(1 for i in ITEMS if i.published_at and i.published_at.year == 2026),
        popularity_filter_count=sum(1 for i in ITEMS if i.like_count and i.like_count > 100),
        category_filter_count=sum(1 for i in ITEMS if i.category != ItemCategory.ASSET),
    )
    features = FeatureStats(
        color_search=color_search,
        style_search=style_search,
        avatar_reverse_search=avatar_rev_search,
        cross_category_search=cross_category_search,
    )

    auditor = QuantitativeAuditor()
    report = auditor.run(ITEMS, crawl=crawl_stats, filters=filters, features=features)

    md = f"""# SEO Audit Report for BoothItemManager2

## 1. Overall Score
*   **Final Reliability Score**: {report.final_score}
*   **Feature Coverage Score**: {report.feature_coverage_score}

## 2. Coverage Metrics
*   **Total Items**: {report.total_items}
*   **Items with Metadata**: {report.items_with_metadata} ({report.coverage_rate * 100:.2f}%)
*   **Items with Tags**: {report.items_with_tags} ({report.tagging_rate * 100:.2f}%)
*   **Items Missing Critical Fields**: {report.items_missing_fields} ({report.missing_rate * 100:.2f}%)

## 3. Tag Quality Metrics
*   **Tagged Items Count**: {report.tagged_items}
*   **Invalid Tags Found**: {report.invalid_tags}
*   **Duplicate Tags Found**: {report.duplicate_tags}
*   **Category-Tag Mismatches**: {report.category_tag_mismatches}
*   **Valid Tag Rate**: {report.valid_tag_rate * 100:.2f}%

## 4. Crawl & Indexing Sync
*   **Source Items Crawled**: {report.source_items}
*   **Indexed Items**: {report.indexed_items}
*   **Lost Items**: {report.lost_items}
*   **Sync Rate**: {report.sync_rate * 100:.2f}%

## 5. Filter Constraint Status
*   **Year Filter**: {report.year_filter.status} (evidence: {report.year_filter.evidence_count})
*   **Popularity Filter**: {report.popularity_filter.status} (evidence: {report.popularity_filter.evidence_count})
*   **Category Filter**: {report.category_filter.status} (evidence: {report.category_filter.evidence_count})

## 6. Search Feature Support
*   **Color Search**: {report.color_search} items supported
*   **Style Search**: {report.style_search} items supported
*   **Avatar Reverse Search**: {report.avatar_reverse_search} items supported
*   **Cross Category Search**: {report.cross_category_search} items supported
"""
    return md


# Dispatch request to handlers
def dispatch(method: str, params: dict[str, Any]) -> Any:
    """Dispatches the JSON-RPC call to the appropriate handler."""
    if method == "get_catalog_summary":
        return handle_get_catalog_summary(params)
    elif method == "get_seo_audit":
        return handle_get_seo_audit(params)
    elif method == "inspect_item_seo":
        return handle_inspect_item_seo(params)
    elif method == "list_items_by_seo_status":
        return handle_list_items_by_seo_status(params)
    elif method == "suggest_seo_optimizations":
        return handle_suggest_seo_optimizations(params)
    else:
        raise ValueError(f"Unknown tool method: {method}")


def main() -> None:
    """Main input loop parsing JSON-RPC over standard input."""
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdin.reconfigure(encoding="utf-8")

    log("Initializing Model Context Protocol (MCP) Server...")
    load_data()
    log("Server initialized and listening for requests.")

    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break

            request = json.loads(line.strip())

            req_id = request.get("id")
            method = request.get("method")
            params = request.get("params", {})

            if method == "initialize":
                response = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {"resources": {}, "tools": {}},
                        "serverInfo": {"name": "boothitemmanager2-seo-server", "version": "0.1.0"},
                    },
                }
            elif method == "notifications/initialized":
                continue
            elif method == "resources/list":
                response = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "resources": [
                            {
                                "uri": "seo://audit/report",
                                "name": "SEO Audit Report",
                                "description": "Site-wide SEO audit report detailing metadata quality and indexing status.",
                                "mimeType": "text/markdown",
                            },
                            {
                                "uri": "catalog://summary",
                                "name": "Catalog Summary",
                                "description": "Brief statistical overview of the catalog's categories and tags.",
                                "mimeType": "application/json",
                            },
                        ]
                    },
                }
            elif method == "resources/read":
                uri = params.get("uri")
                if uri == "seo://audit/report":
                    content = get_markdown_audit_report()
                    mime = "text/markdown"
                elif uri == "catalog://summary":
                    content = handle_get_catalog_summary({})
                    mime = "application/json"
                else:
                    raise ValueError(f"Unknown resource URI: {uri}")

                response = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"contents": [{"uri": uri, "mimeType": mime, "text": content}]},
                }
            elif method == "tools/list":
                response = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "tools": [
                            {
                                "name": "get_catalog_summary",
                                "description": "Get general catalog metrics including total item count, category breakdown, tags frequency, and price statistics.",
                                "inputSchema": {"type": "object", "properties": {}},
                            },
                            {
                                "name": "get_seo_audit",
                                "description": "Get site-wide SEO audit report detailing overall scores, missing metadata counts, tag quality issues, and crawler sync rate.",
                                "inputSchema": {"type": "object", "properties": {}},
                            },
                            {
                                "name": "inspect_item_seo",
                                "description": "Inspect a specific item's SEO metadata quality checklist (e.g. title length, description presence, tag counts, similar items mapping) and get a pass/fail assessment.",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "item_id": {
                                            "type": "string",
                                            "description": "The unique BOOTH item ID to audit.",
                                        }
                                    },
                                    "required": ["item_id"],
                                },
                            },
                            {
                                "name": "list_items_by_seo_status",
                                "description": "Retrieve items filtered by their SEO audit status (PASS/FAIL/UNVERIFIED) or specific failures (e.g., missing description, low tags count).",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "status": {
                                            "type": "string",
                                            "enum": ["PASS", "FAIL", "UNVERIFIED"],
                                            "description": "Filter by general SEO status.",
                                        },
                                        "issue": {
                                            "type": "string",
                                            "enum": [
                                                "missing_description",
                                                "missing_targets",
                                                "low_tag_count",
                                                "no_similar_items",
                                            ],
                                            "description": "Filter by a specific SEO issue.",
                                        },
                                        "limit": {
                                            "type": "integer",
                                            "default": 10,
                                            "description": "Maximum number of items to return.",
                                        },
                                    },
                                },
                            },
                            {
                                "name": "suggest_seo_optimizations",
                                "description": "Get recommendations for optimizing a specific item's SEO title, description, and tags based on catalog ontology rules.",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "item_id": {
                                            "type": "string",
                                            "description": "The unique BOOTH item ID to generate suggestions for.",
                                        }
                                    },
                                    "required": ["item_id"],
                                },
                            },
                        ]
                    },
                }
            elif method == "tools/call":
                tool_name = params.get("name", "")
                tool_args = params.get("arguments", {})
                tool_result = dispatch(tool_name, tool_args)
                response = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"content": [{"type": "text", "text": tool_result}]},
                }
            else:
                response = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Method '{method}' not found"},
                }

            sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            sys.stdout.flush()

        except Exception as e:
            import traceback

            traceback.print_exc(file=sys.stderr)
            sys.stderr.flush()

            try:
                err_response = {
                    "jsonrpc": "2.0",
                    "id": locals().get("req_id"),
                    "error": {"code": -32603, "message": str(e)},
                }
                sys.stdout.write(json.dumps(err_response, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except Exception:
                pass


if __name__ == "__main__":
    main()
