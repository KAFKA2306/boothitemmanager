#!/usr/bin/env python3
"""
seo_autofix.py - Automatic SEO and AEO Defect Checker and Fixer
===============================================================
Checks index.html for SEO/AEO violations and automatically applies fixes.
Follows Zero-Fat (strict logic, no bloat) and Crash-Driven Development.
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any
from bs4 import BeautifulSoup

DEFAULT_HTML_PATH = Path("index.html")
DEFAULT_REPORT_PATH = Path("docs/seo_report.md")


def audit_html_structure(html_content: str) -> dict[str, Any]:
    """
    Parses and checks the HTML structure for basic SEO/AEO elements.
    Raises errors if critical assumptions are broken, conforming to CDD.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    errors: list[str] = []
    warnings: list[str] = []
    fixes_needed: dict[str, Any] = {}

    # 1. Check html lang attribute
    html_tag = soup.find("html")
    assert html_tag is not None, "HTML root tag not found!"
    lang = html_tag.get("lang")
    if not lang:
        errors.append("HTML 'lang' attribute is missing")
        fixes_needed["lang"] = "ja"
    elif lang not in ["ja", "en"]:
        warnings.append(f"HTML 'lang' attribute '{lang}' is not standard for this project (expected 'ja' or 'en')")

    # 2. Check title tag
    title_tag = soup.find("title")
    if not title_tag or not title_tag.string:
        errors.append("Title tag is missing or empty")
        fixes_needed["title"] = "BoothItemManager2 - VRChat Booth Asset Discovery"
    else:
        title_len = len(title_tag.string.strip())
        if title_len < 10:
            warnings.append(f"Title is too short ({title_len} chars): '{title_tag.string}'")
        elif title_len > 70:
            warnings.append(f"Title is too long ({title_len} chars): '{title_tag.string}'")

    # 3. Check description meta tag
    desc_tag = soup.find("meta", attrs={"name": "description"})
    if not desc_tag or not desc_tag.get("content"):
        errors.append("Meta description tag is missing or empty")
        fixes_needed["description"] = (
            "Discover VRChat virtual assets, outfits, accessories, hairstyles, and gimmicks from Booth.pm. "
            "Filter instantly by base avatar compatibility, style, color, category, and price."
        )
    else:
        desc_len = len(desc_tag.get("content", "").strip())
        if desc_len < 50:
            warnings.append(f"Meta description is too short ({desc_len} chars)")
        elif desc_len > 160:
            warnings.append(f"Meta description is too long ({desc_len} chars)")

    # 4. Check canonical link tag
    canonical_tag = soup.find("link", attrs={"rel": "canonical"})
    if not canonical_tag or not canonical_tag.get("href"):
        errors.append("Canonical link tag is missing or empty")
        fixes_needed["canonical"] = "https://boothitemmanager.pages.dev/"

    # 5. Check JSON-LD
    json_ld_tags = soup.find_all("script", attrs={"type": "application/ld+json"})
    if not json_ld_tags:
        errors.append("JSON-LD structured data is missing")
        fixes_needed["json_ld"] = True
    else:
        # Validate that all found JSON-LD tags parse as valid JSON (Crash-driven)
        for tag in json_ld_tags:
            json.loads(tag.string)

    # 6. Check for standard image tags missing alt attributes (Soup check)
    img_tags = soup.find_all("img")
    missing_soup_alts = 0
    for img in img_tags:
        if not img.get("alt"):
            missing_soup_alts += 1
    if missing_soup_alts > 0:
        errors.append(f"Found {missing_soup_alts} standard img tags missing alt attribute")
        fixes_needed["img_alts"] = True

    return {
        "errors": errors,
        "warnings": warnings,
        "fixes_needed": fixes_needed,
    }


def apply_fixes(html_content: str, audit_results: dict[str, Any]) -> tuple[str, list[str]]:
    """
    Applies targeted string and regex fixes to the HTML content to avoid complete file reformatting.
    """
    fixes_applied: list[str] = []
    modified_content = html_content
    fixes_needed = audit_results["fixes_needed"]

    # 1. Fix lang attribute
    if "lang" in fixes_needed:
        # Regex to replace <html> with <html lang="ja">
        modified_content = re.sub(r"<html([^>]*)>", r'<html\1 lang="ja">', modified_content, count=1)
        fixes_applied.append("Added lang='ja' to <html> tag.")

    # Helper to insert into <head>
    def insert_in_head(content: str, new_tag: str) -> str:
        # Find position right after <head>
        head_match = re.search(r"<head[^>]*>", content, re.IGNORECASE)
        if head_match:
            idx = head_match.end()
            return content[:idx] + f"\n    {new_tag}" + content[idx:]
        return content

    # 2. Fix title
    if "title" in fixes_needed:
        title_val = fixes_needed["title"]
        # If title tag is completely missing, insert it. If empty, replace it.
        if "<title" in modified_content:
            modified_content = re.sub(
                r"<title[^>]*>.*?</title>",
                f"<title>{title_val}</title>",
                modified_content,
                flags=re.IGNORECASE,
            )
        else:
            modified_content = insert_in_head(modified_content, f"<title>{title_val}</title>")
        fixes_applied.append(f"Set title to '{title_val}'")

    # 3. Fix description
    if "description" in fixes_needed:
        desc_val = fixes_needed["description"]
        new_meta = f'<meta name="description" content="{desc_val}">'
        if 'name="description"' in modified_content or "name='description'" in modified_content:
            modified_content = re.sub(
                r'<meta\s+name=["\']description["\']\s+content=["\'].*?["\']\s*/?>',
                new_meta,
                modified_content,
                flags=re.IGNORECASE,
            )
        else:
            modified_content = insert_in_head(modified_content, new_meta)
        fixes_applied.append("Added meta description tag")

    # 4. Fix canonical link
    if "canonical" in fixes_needed:
        canonical_val = fixes_needed["canonical"]
        new_link = f'<link rel="canonical" href="{canonical_val}">'
        modified_content = insert_in_head(modified_content, new_link)
        fixes_applied.append(f"Added canonical link to {canonical_val}")

    # 5. Fix JSON-LD if missing
    if "json_ld" in fixes_needed:
        default_json_ld = {
            "@context": "https://schema.org",
            "@type": "WebApplication",
            "name": "BoothItemManager2",
            "url": "https://boothitemmanager.pages.dev/",
            "description": "Discover VRChat virtual assets, outfits, accessories, hairstyles, and gimmicks from Booth.pm.",
            "applicationCategory": "SearchEngine",
            "operatingSystem": "All",
        }
        json_ld_script = (
            f'<script type="application/ld+json">\n    {json.dumps(default_json_ld, indent=2)}\n    </script>'
        )
        modified_content = insert_in_head(modified_content, json_ld_script)
        fixes_applied.append("Added missing JSON-LD structured data")

    # 6. Fix missing image alt attributes (both standard and inside JS template literals)
    # Using the regex to check every <img ...> tag.
    img_pattern = re.compile(r"<img\s+[^>]*>", re.IGNORECASE)
    matches = img_pattern.findall(modified_content)

    img_fix_count = 0
    for match in set(matches):
        if not re.search(r"\balt\s*=\s*", match, re.IGNORECASE):
            # No alt tag! Add default
            if match.endswith("/>"):
                replacement = match[:-2].rstrip() + ' alt="Asset Preview" />'
            else:
                replacement = match[:-1].rstrip() + ' alt="Asset Preview">'
            modified_content = modified_content.replace(match, replacement)
            img_fix_count += 1

    if img_fix_count > 0:
        fixes_applied.append(f"Added alt='Asset Preview' to {img_fix_count} <img> tags (including template strings)")

    return modified_content, fixes_applied


def write_kawaii_report(report_path: Path, audit_results: dict[str, Any], fixes_applied: list[str]) -> None:
    """
    Writes the audit report in cute Japanese (kawaii style) as mandated.
    """
    report_path.parent.mkdir(parents=True, exist_ok=True)

    status_emoji = "🎀✨ココちゃん完璧だょ！✨🎀" if not audit_results["errors"] and not fixes_applied else "🌸なおしたょ！がんばったもん！🌸"

    lines = [
        f"# 🎀 SEO/AEO 診断＆自動お直しレポートだょ 🎀",
        "",
        f"ココちゃんがお部屋（index.html）のSEOとAEO（AI検索最適化）をチェックしたよぉ！(⑅•ᴗ•⑅)◜..°♡",
        f"現在のステータス： **{status_emoji}**",
        "",
        "## 🌸 診断結果 (Audit Results) 🌸",
        "",
    ]

    if audit_results["errors"]:
        lines.append("### 🚨 みつかった問題点 (Errors) 🚨")
        for err in audit_results["errors"]:
            lines.append(f"- {err} 💦")
        lines.append("")

    if audit_results["warnings"]:
        lines.append("### ⚠️ ちゅうい事項 (Warnings) ⚠️")
        for warn in audit_results["warnings"]:
            lines.append(f"- {warn} 🥺")
        lines.append("")

    if not audit_results["errors"] and not audit_results["warnings"]:
        lines.append("### 🌟 もんだいなし！ 🌟")
        lines.append("カンペキ！とってもきれいでAIさんたちも大よろこびだょっ！💮")
        lines.append("")

    lines.append("## 🛠️ お直ししたところ (Fixes Applied) 🛠️")
    lines.append("")

    if fixes_applied:
        for fix in fixes_applied:
            lines.append(f"- **{fix}** をがんばってなおしたよぉ！きゃはっ✨")
    else:
        lines.append("お直しするところはなかったよ！とってもおりこうさんだもん！🍭")

    lines.append("")
    lines.append("---")
    lines.append("ココちゃんがお届けしましたっ！これからもステキなお部屋をつくろうねっ！(⑅•ᴗ•⑅)♡")

    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Auto-fix SEO and AEO issues in index.html")
    parser.add_argument("--html", type=Path, default=DEFAULT_HTML_PATH, help="Path to index.html")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH, help="Path to write kawaii markdown report")
    args = parser.parse_args()

    html_path: Path = args.html
    report_path: Path = args.report

    # Ensure input file exists (Crash-driven: will raise exception if not found)
    assert html_path.exists(), f"Input file not found at: {html_path}"

    content = html_path.read_text(encoding="utf-8")

    # Run audit
    audit_results = audit_html_structure(content)

    # Apply fixes
    fixed_content, fixes_applied = apply_fixes(content, audit_results)

    # Write report in cute Japanese
    write_kawaii_report(report_path, audit_results, fixes_applied)

    # Save fixed html if changes were made
    if fixes_applied:
        html_path.write_text(fixed_content, encoding="utf-8")
        print(f"SUCCESS: SEO defects fixed. Applied: {', '.join(fixes_applied)}")
        sys.exit(0)
    else:
        print("SUCCESS: No SEO defects found or auto-fixes needed.")
        sys.exit(0)


if __name__ == "__main__":
    main()
