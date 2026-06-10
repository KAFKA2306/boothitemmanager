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
        try:
            return int(elem.get("data-wishlist-count"))
        except Exception:
            pass
    button = soup.select_one(".wish-list-button")
    if button:
        count_text = button.get_text(strip=True)
        match = re.search("(\\d+)", count_text)
        if match:
            return int(match.group(1))
    return 0


def _pick_published_at(soup: BeautifulSoup, json_ld: dict[str, Any] | None) -> datetime | None:
    if json_ld and json_ld.get("releaseDate"):
        try:
            return datetime.fromisoformat(json_ld["releaseDate"].replace("Z", "+00:00"))
        except Exception:
            pass
    date_elem = soup.select_one(".base-datetime")
    if date_elem:
        date_str = date_elem.get_text(strip=True)
        try:
            return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        except Exception:
            pass
    time_tag = soup.find("time")
    if time_tag and time_tag.get("datetime"):
        try:
            return datetime.fromisoformat(time_tag["datetime"].replace("Z", "+00:00"))
        except Exception:
            pass
    return None


def normalize_html(raw_page: Any, trace_id: str) -> TestBlock:
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
    targets = pick_targets(title, description, tags_raw, aliases)
    category = infer_category(title, description, tags_raw, targets, aliases)
    tag_set = extract_tag_set(title, description, tags_raw, targets, aliases)
    files = _pick_files(soup)
    like_count = _pick_like_count(soup)
    published_at = _pick_published_at(soup, json_ld)
    item = Item(
        item_id=item_id,
        source_url=raw_page.url,
        title=title,
        description=description,
        thumbnail_url=thumbnail_url or "",
        creator_id=creator_id or "unknown",
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
        # Fallback to old path if ontology dir doesn't exist yet
        old_path = os.path.join(os.getcwd(), "aliases.yml")
        if os.path.exists(old_path):
            with open(old_path, encoding="utf-8") as f:
                return yaml.safe_load(f)
        return {}
    
    res = {}
    try:
        avatars = yaml.safe_load(open(os.path.join(ontology_dir, "avatars.yaml"), encoding="utf-8"))
        # Map canonical format to old aliases.yml format for backward compatibility
        res["avatars"] = {}
        for code, data in avatars.get("avatars", {}).items():
            res["avatars"][code] = {
                "name_ja": data.get("canonical_name"),
                "item_id": data.get("booth_item_id"),
                "aliases": data.get("aliases", [])
            }
        
        tags = yaml.safe_load(open(os.path.join(ontology_dir, "tags.yaml"), encoding="utf-8"))
        res["categories"] = tags.get("categories", {})
        res["features"] = tags.get("features", {})
        
        styles = yaml.safe_load(open(os.path.join(ontology_dir, "styles.yaml"), encoding="utf-8"))
        res["styles"] = styles.get("styles", {})
        
    except Exception as e:
        print(f"⚠️ Warning: Failed to load granular ontology: {e}")
        # Final fallback
        old_path = os.path.join(os.getcwd(), "aliases.yml")
        if os.path.exists(old_path):
            with open(old_path, encoding="utf-8") as f:
                return yaml.safe_load(f)
                
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
            try:
                data = json.loads(script.string)
                return data[0] if isinstance(data, list) else data
            except Exception:
                pass
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
    try:
        if json_ld and "offers" in json_ld:
            return int(float(str(json_ld["offers"]["price"]).replace(",", "")))
        if "price:amount" in og_data:
            return int(float(og_data["price:amount"].replace(",", "")))
    except Exception:
        pass
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
    NEGATIONS = ["非対応", "不可", "except", "not supported", "not compatible", "除外", "のみ対応", "なし", "not"]

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
        terms = list(set([code.lower()] + [
            t.lower()
            for t in data.get("aliases", []) + [name_ja, name_en]
            if t
        ]))
        
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
                
                is_negated = any(n in window_before for n in NEGATIONS) or \
                             any(n in window_after for n in NEGATIONS)
                
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
    if any(k in text for k in ["vroid", "vroidhub"]):
        return ItemCategory.VROID
    if any(k in text for k in ["アニメーション", "motion", "モーション", "animation"]):
        return ItemCategory.ANIMATION
    if any(k in text for k in ["髪型", "ヘアスタイル", "hairstyle", "髪"]):
        return ItemCategory.HAIRSTYLE
    if any(k in text for k in ["アバター", "avatar"]) and "対応" not in name:
        return ItemCategory.AVATAR
    if any(k in text for k in ["衣装", "服", "outfit", "costume", "dress"]):
        return ItemCategory.OUTFIT
    if any(k in text for k in ["アクセ", "accessory", "靴", "メガネ", "帽子"]):
        return ItemCategory.ACCESSORY
    if any(k in text for k in ["テクスチャ", "texture", "瞳", "肌", "skin"]):
        return ItemCategory.TEXTURE
    if any(k in text for k in ["ワールド", "world", "scene", "シーン"]):
        return ItemCategory.WORLD
    if any(k in text for k in ["ギミック", "gimmick", "modular", "ma対応", "tool", "ツール"]):
        return ItemCategory.GIMMICK_TOOL
    if any(k in text for k in ["小道具", "prop", "家具", "椅子", "机"]):
        return ItemCategory.PROP
    return ItemCategory.ASSET


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
    }
    
    # 1. Categories mapping (Sub-categories into appropriate dimensions)
    cat_mapping = {
        "OUTFIT": "outfit_type",
        "ACCESSORY": "accessory",
        "HAIRSTYLE": "appearance",
        "TEXTURE": "appearance"
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

    # Deduplicate
    for key in res:
        res[key] = list(set(res[key]))

    return TagSet(**res)
