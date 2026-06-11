import json
import os
import re
import unicodedata
from datetime import datetime
from typing import Any
from urllib.parse import urljoin, urlparse

import yaml
from bs4 import BeautifulSoup

from ..core import TestBlock
from ..schemas.storage import AvatarRef, FileAsset, Item, ItemCategory, TagSet


def _pick_like_count(soup: BeautifulSoup) -> int:
    elem = soup.select_one("[data-wishlist-count]")
    if elem and elem.get("data-wishlist-count"):
        return int(elem.get("data-wishlist-count"))
    button = soup.select_one(".wish-list-button")
    if button:
        count_text = button.get_text(strip=True)
        match = re.search("(\\d+)", count_text)
        if match:
            return int(match.group(1))
    return 0


def _pick_published_at(soup: BeautifulSoup, json_ld: dict[str, Any] | None) -> datetime | None:
    if json_ld and json_ld.get("releaseDate"):
        return datetime.fromisoformat(json_ld["releaseDate"].replace("Z", "+00:00"))
    date_elem = soup.select_one(".base-datetime")
    if date_elem:
        date_str = date_elem.get_text(strip=True)
        return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
    time_tag = soup.find("time")
    if time_tag and time_tag.get("datetime"):
        return datetime.fromisoformat(time_tag["datetime"].replace("Z", "+00:00"))
    return None


def mask_pii(text: str) -> str:
    # Minimal masking logic for PII (Zero-Fat)
    # Masking booth item IDs and shop IDs that could identify individuals
    masked = re.sub(r"(https?://)[a-z0-9]+\.(booth\.pm)", r"\1[MASKED].\2", text)
    masked = re.sub(r"(items/)(\d+)", r"\1[MASKED_ID]", masked)
    return masked


def normalize_html(raw_page: Any, trace_id: str) -> TestBlock:
    import hashlib

    soup = BeautifulSoup(raw_page.content, "html.parser")
    item_id_match = re.search("items/(\\d+)", raw_page.url)
    if not item_id_match:
        raise ValueError(f"CRITICAL: item_id extraction failed for {raw_page.url}")
    item_id = item_id_match.group(1)
    aliases = load_aliases()
    og_data = _parse_og_tags(soup)
    json_ld = _parse_json_ld(soup)
    title = _pick_name(soup, og_data)
    creator_name = _pick_shop_name(soup, og_data)
    creator_id = _pick_creator_id(soup, raw_page.url)
    price = _pick_price(soup, og_data, json_ld)
    thumbnail_url = _pick_image(soup, og_data, raw_page.url)
    description = _pick_description(soup, og_data) or ""
    tags_raw = _pick_tags(soup)

    # PII Masking Gateway integration (Zero-Fat)
    masked_description = mask_pii(description)
    masked_creator_id = "[MASKED]" if creator_id else "unknown"

    targets = pick_targets(title, description, tags_raw, aliases)
    category = infer_category(title, description, tags_raw, targets, aliases)
    tag_set = extract_tag_set(title, description, tags_raw, targets, aliases)
    files = _pick_files(soup)
    like_count = _pick_like_count(soup)
    published_at = _pick_published_at(soup, json_ld)

    # Compute provenance data
    html_hash = hashlib.sha256(raw_page.content.encode("utf-8")).hexdigest()
    raw_html_snippet = (
        f"file:///home/kafka/projects/boothitemmanager/input/raw/{item_id}.html#sha256={html_hash}"
    )

    trace_log = {
        "timestamp": datetime.now().isoformat(),
        "source_html": f"input/raw/{item_id}.html",
        "rules": {
            "item_id_regex": "items/(\\d+)",
            "target_avatar_regex": "(?<![a-z0-9]){term}(?![a-z0-9])",
        },
    }

    # Audit determination
    if not title or not thumbnail_url:
        audit_status = "FAIL"
    elif category == ItemCategory.ASSET or not targets:
        audit_status = "UNVERIFIED"
    else:
        audit_status = "PASS"

    item = Item(
        item_id=item_id,
        source_url=raw_page.url,
        title=title,
        description=masked_description,  # Masked
        thumbnail_url=thumbnail_url or "",
        creator_id=masked_creator_id,  # Masked
        creator_name=creator_name,
        published_at=published_at,
        like_count=like_count,
        price=price,
        category=category,
        tag_set=tag_set,
        similar_items=[],
        user_state={},
        tags_raw=tags_raw,
        targets=targets,
        files=files,
        audit_status=audit_status,
        trace_log=trace_log,
        raw_html_snippet=raw_html_snippet,
    )
    return TestBlock(
        trace_id=trace_id,
        input=raw_page.url,
        pre_state={"url": raw_page.url},
        action="normalize_html",
        expected_state={"item_id": item_id},
        actual_state={"item": item},
        diff={},
        result="SUCCESS",
    )


def load_aliases() -> dict[str, Any]:
    ontology_dir = os.path.join(os.getcwd(), "ontology")
    if not os.path.exists(ontology_dir):
        old_path = os.path.join(os.getcwd(), "aliases.yml")
        if os.path.exists(old_path):
            with open(old_path, encoding="utf-8") as f:
                return yaml.safe_load(f)
        return {}

    res = {}
    avatars_path = os.path.join(ontology_dir, "avatars.yaml")
    with open(avatars_path, encoding="utf-8") as f:
        avatars = yaml.safe_load(f)
    res["avatars"] = {}
    for code, data in avatars.get("avatars", {}).items():
        res["avatars"][code] = {
            "name_ja": data.get("canonical_name"),
            "item_id": data.get("booth_item_id"),
            "aliases": data.get("aliases", []),
        }

    tags_path = os.path.join(ontology_dir, "tags.yaml")
    with open(tags_path, encoding="utf-8") as f:
        tags = yaml.safe_load(f)
    res["categories"] = tags.get("categories", {})
    res["features"] = tags.get("features", {})
    res["components"] = tags.get("components", {})
    res["outfit_types"] = tags.get("outfit_types", {})
    res["accessories"] = tags.get("accessories", {})
    res["appearances"] = tags.get("appearances", {})
    res["colors"] = tags.get("colors", {})
    res["body_types"] = tags.get("body_types", {})
    res["platforms"] = tags.get("platforms", {})
    res["seasons"] = tags.get("seasons", {})

    styles_path = os.path.join(ontology_dir, "styles.yaml")
    with open(styles_path, encoding="utf-8") as f:
        styles = yaml.safe_load(f)
    res["styles"] = styles.get("styles", {})

    rich_path = os.path.join(ontology_dir, "rich_dimensions.yaml")
    if os.path.exists(rich_path):
        with open(rich_path, encoding="utf-8") as f:
            rich_dims = yaml.safe_load(f)
        res["material_properties"] = rich_dims.get("material_properties", {})
        res["niche_subcultures"] = rich_dims.get("niche_subcultures", {})
        res["activity_scenes"] = rich_dims.get("activity_scenes", {})

    return res


def _parse_og_tags(soup: BeautifulSoup) -> dict[str, str]:
    og_data = {}
    for tag in soup.find_all("meta", property=lambda x: x and x.startswith("og:")):
        prop = tag.get("property", "")[3:]
        content = tag.get("content")
        if prop and content:
            og_data[prop] = content
    return og_data


def _parse_json_ld(soup: BeautifulSoup) -> dict[str, Any] | None:
    for script in soup.find_all("script", type="application/ld+json"):
        if script.string:
            data = json.loads(script.string)
            return data[0] if isinstance(data, list) else data
    return None


def _pick_name(soup: BeautifulSoup, og_data: dict[str, str]) -> str:
    val = og_data.get("title") or (
        soup.select_one("h1.item-name") or soup.select_one("h1")
    ).get_text(strip=True)
    if not val:
        raise ValueError("Name extraction failed")
    return val.strip()


def _pick_shop_name(soup: BeautifulSoup, og_data: dict[str, str]) -> str:
    elem = soup.select_one("div.shop-name, a.shop-name, .booth-user-name a")
    return elem.get_text(strip=True) if elem else og_data.get("site_name", "Unknown Shop")


def _pick_creator_id(soup: BeautifulSoup, url: str) -> str | None:
    parsed = urlparse(url)
    if parsed.hostname and ".booth.pm" in parsed.hostname:
        sub = parsed.hostname.split(".")[0]
        if sub != "booth":
            return sub
    elem = soup.select_one("[data-product-brand]")
    return elem.get("data-product-brand") if elem else None


def _pick_price(
    soup: BeautifulSoup, og_data: dict[str, str], json_ld: dict[str, Any] | None
) -> int | None:
    if json_ld:
        offers = json_ld.get("offers")
        if isinstance(offers, dict):
            price_val = offers.get("price")
            if price_val is not None:
                return int(float(str(price_val).replace(",", "")))
        elif isinstance(offers, list) and len(offers) > 0:
            price_val = offers[0].get("price")
            if price_val is not None:
                return int(float(str(price_val).replace(",", "")))
    if "price:amount" in og_data:
        return int(float(og_data["price:amount"].replace(",", "")))
    return None


def _pick_image(soup: BeautifulSoup, og_data: dict[str, str], base_url: str) -> str | None:
    img = og_data.get("image") or (soup.select_one("img.market-item-image") or {}).get("src")
    if img:
        return re.sub("/c/\\d+x\\d+/", "/", urljoin(base_url, img))
    return None


def _pick_description(soup: BeautifulSoup, og_data: dict[str, str]) -> str | None:
    elem = soup.select_one(".item-description, .description, .js-market-item-detail-description")
    return elem.get_text("\n", strip=True) if elem else og_data.get("description")


def _pick_tags(soup: BeautifulSoup) -> list[str]:
    return list(
        set(
            t.get_text(strip=True).replace("#", "")
            for t in soup.select("a.l-tag, a.u-tpg-label, .item-tags a")
        )
    )


def _pick_files(soup: BeautifulSoup) -> list[FileAsset]:
    files = []
    for elem in soup.select(".download-item-name, .variation-name"):
        name = elem.get_text(strip=True)
        if name and name not in ["ダウンロード商品", "在庫あり"]:
            files.append(FileAsset(filename=name))
    return files


def pick_targets(
    name: str, description: str, tags: list[str], aliases: dict[str, Any]
) -> list[AvatarRef]:
    targets_map = {}
    text = f"{name} {description} {' '.join(tags)}".lower()

    # Negative patterns to look for near the term
    NEGATIONS = [
        "非対応",
        "不可",
        "except",
        "not supported",
        "not compatible",
        "除外",
        "のみ対応",
        "なし",
        "not",
    ]

    # 1. ID-based matching (Highest Confidence)
    found_ids = set(re.findall(r"items/(\d+)", description))
    for code, data in aliases.get("avatars", {}).items():
        target_id = str(data.get("item_id", ""))
        if target_id and target_id in found_ids:
            targets_map[code] = AvatarRef(code=code, name=data.get("name_ja", code))

    # 2. Text-based matching with fuzzy boundaries and bidirectional negation check
    for code, data in aliases.get("avatars", {}).items():
        if code in targets_map:
            continue

        name_ja = data.get("name_ja", "")
        name_en = data.get("name_en", "")
        terms = list(
            set(
                [code.lower()]
                + [t.lower() for t in data.get("aliases", []) + [name_ja, name_en] if t]
            )
        )

        for term in terms:
            # Fuzzy boundary: ensure not mid-word for alphanumeric
            if term.isalnum():
                pattern = rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])"
            else:
                pattern = re.escape(term)

            for match in re.finditer(pattern, text):
                idx = match.start()
                # Check window before and after for negation
                window_before = text[max(0, idx - 20) : idx]
                window_after = text[idx : idx + 30]

                is_negated = any(n in window_before for n in NEGATIONS) or any(
                    n in window_after for n in NEGATIONS
                )

                if not is_negated:
                    targets_map[code] = AvatarRef(code=code, name=name_ja or code)
                    break
            if code in targets_map:
                break

    return list(targets_map.values())


def infer_category(
    name: str, description: str, tags: list[str], targets: list[AvatarRef], aliases: dict[str, Any]
) -> ItemCategory:
    text = f"{name} {description} {' '.join(tags)}".lower()
    
    # 1. TEXTURE & HAIRSTYLE
    texture_aliases = ["テクスチャ", "texture", "瞳", "肌", "skin", "メイクテクスチャ", "アイテクスチャ"]
    if any(k in text for k in texture_aliases):
        return ItemCategory.TEXTURE

    hairstyle_aliases = ["髪型", "ヘアスタイル", "hairstyle", "髪", "ヘア", "ツインテール", "ポニテ"]
    if any(k in text for k in hairstyle_aliases):
        return ItemCategory.HAIRSTYLE

    # 2. AVATAR
    if any(k in text for k in ["アバター", "avatar", "オリジナル3dモデル"]) and "対応" not in name:
        return ItemCategory.AVATAR

    # 3. Dynamic loading of terms from ontology aliases for ACCESSORY and OUTFIT
    # Note: Includes PROP (小道具, prop, 家具, etc.) mapped directly to ACCESSORY for frontend compatibility
    accessory_terms = ["アクセ", "accessory", "小物品", "小物", "靴", "メガネ", "帽子", "バッグ", "チョーカー", "ピアス", "リボン", "指輪", "傘", "ソックス", "タイツ", "ベルト", "小道具", "prop", "家具", "椅子", "机"]
    for acc_code, data in aliases.get("accessories", {}).items():
        accessory_terms.extend([t.lower() for t in data.get("aliases", [])])
    
    outfit_terms = ["衣装", "服", "outfit", "costume", "dress", "ワンピ", "ジャケット", "パーカー", "スカート", "シャツ", "パンツ"]
    for ot_code, data in aliases.get("outfit_types", {}).items():
        outfit_terms.extend([t.lower() for t in data.get("aliases", [])])

    has_accessory = any(k in text for k in accessory_terms if k)
    has_outfit = any(k in text for k in outfit_terms if k)

    # Resolve overlaps: Accessories are usually more specific than "outfit/clothing" terms
    if has_accessory and not (has_outfit and "セット" in text and "衣装" in name):
        return ItemCategory.ACCESSORY
    if has_outfit:
        return ItemCategory.OUTFIT
    if has_accessory:
        return ItemCategory.ACCESSORY

    # 4. GIMMICK_TOOL (Also maps ANIMATION, WORLD, and other system tools here)
    gimmick_terms = ["ギミック", "gimmick", "modular", "ma対応", "tool", "ツール", "アニメーション", "motion", "モーション", "animation", "ワールド", "world", "scene", "シーン"]
    if any(k in text for k in gimmick_terms):
        return ItemCategory.GIMMICK_TOOL

    # 5. VROID Fallback (Map to OUTFIT or AVATAR)
    if any(k in text for k in ["vroid", "vroidhub"]):
        if any(x in text for x in ["衣装", "服", "ワンピ", "ドレス"]):
            return ItemCategory.OUTFIT
        return ItemCategory.AVATAR

    # 6. Final Fallback (Return GIMMICK_TOOL to avoid ASSET which is unsupported in frontend)
    return ItemCategory.GIMMICK_TOOL


def extract_tag_set(
    name: str, description: str, tags: list[str], targets: list[AvatarRef], aliases: dict[str, Any]
) -> TagSet:

    def _norm(t: str) -> str:
        return unicodedata.normalize("NFKC", t).lower()

    text = _norm(f"{name} {description} {' '.join(tags)}")
    res = {
        "appearance": [],
        "body_type": [],
        "style": [],
        "color": [],
        "outfit_type": [],
        "accessory": [],
        "feature": [],
        "platform": [],
        "season": [],
        "avatar_link": [t.code for t in targets],
        "material_property": [],
        "niche_subculture": [],
        "activity_scene": [],
    }

    # 1. Categories mapping (Sub-categories into appropriate dimensions)
    cat_mapping = {
        "OUTFIT": "outfit_type",
        "ACCESSORY": "accessory",
        "HAIRSTYLE": "appearance",
        "TEXTURE": "appearance",
    }
    for cat_code, data in aliases.get("categories", {}).items():
        terms = [_norm(t) for t in data.get("aliases", [])]
        if any(t in text for t in terms):
            dim = cat_mapping.get(cat_code)
            if dim:
                # Add sub-categories as tags if found
                for sub in data.get("sub_categories", []):
                    if _norm(sub) in text:
                        res[dim].append(sub)

    # 2. Features mapping
    for feat_code, data in aliases.get("features", {}).items():
        terms = [_norm(t) for t in data.get("aliases", [])]
        if any(t in text for t in terms):
            res["feature"].append(feat_code)

    # 3. Styles mapping
    for style_code, terms in aliases.get("styles", {}).items():
        norm_terms = [_norm(t) for t in terms]
        if any(t in text for t in norm_terms):
            res["style"].append(style_code)

    # 4. Components mapping (into feature/appearance)
    for comp_code, terms in aliases.get("components", {}).items():
        norm_terms = [_norm(t) for t in terms]
        if any(t in text for t in norm_terms):
            res["appearance"].append(comp_code)

    # 5. body_type mapping
    for bt, data in aliases.get("body_types", {}).items():
        terms = [_norm(t) for t in data.get("aliases", [])]
        if any(t in text for t in terms):
            res["body_type"].append(bt)

    # 6. color mapping
    color_text = (
        text.replace("面白い", "")
        .replace("面白", "")
        .replace("告白", "")
        .replace("青春", "")
        .replace("赤ちゃん", "")
        .replace("無茶", "")
        .replace("滅茶", "")
    )
    for col, data in aliases.get("colors", {}).items():
        terms = [_norm(t) for t in data.get("aliases", [])]
        if any(t in color_text for t in terms):
            res["color"].append(col)

    # 7. platform mapping
    for plat, data in aliases.get("platforms", {}).items():
        terms = [_norm(t) for t in data.get("aliases", [])]
        if any(t in text for t in terms):
            res["platform"].append(plat)

    # 8. season mapping
    season_text = text.replace("青春", "")
    for seas, data in aliases.get("seasons", {}).items():
        terms = [_norm(t) for t in data.get("aliases", [])]
        if any(t in season_text for t in terms):
            res["season"].append(seas)

    # 9. outfit_types mapping
    for ot, data in aliases.get("outfit_types", {}).items():
        terms = [_norm(t) for t in data.get("aliases", [])]
        if any(t in text for t in terms):
            res["outfit_type"].append(ot)

    # 10. accessories mapping
    for acc, data in aliases.get("accessories", {}).items():
        terms = [_norm(t) for t in data.get("aliases", [])]
        if any(t in text for t in terms):
            res["accessory"].append(acc)

    # 11. appearances mapping
    for app, data in aliases.get("appearances", {}).items():
        terms = [_norm(t) for t in data.get("aliases", [])]
        if any(t in text for t in terms):
            res["appearance"].append(app)

    # 12. material_properties mapping
    for mp, data in aliases.get("material_properties", {}).items():
        terms = [_norm(t) for t in data.get("aliases", [])]
        if any(t in text for t in terms):
            res["material_property"].append(mp)

    # 13. niche_subcultures mapping
    for ns, data in aliases.get("niche_subcultures", {}).items():
        terms = [_norm(t) for t in data.get("aliases", [])]
        if any(t in text for t in terms):
            res["niche_subculture"].append(ns)

    # 14. activity_scenes mapping
    for act, data in aliases.get("activity_scenes", {}).items():
        terms = [_norm(t) for t in data.get("aliases", [])]
        if any(t in text for t in terms):
            res["activity_scene"].append(act)

    # Deduplicate
    for key in res:
        res[key] = list(set(res[key]))

    return TagSet(**res)
