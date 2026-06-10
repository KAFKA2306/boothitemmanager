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
    path = os.path.join(os.getcwd(), "aliases.yml")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


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
    targets = []
    text = f"{name} {description} {' '.join(tags)}".lower()
    for code, data in aliases.get("avatars", {}).items():
        terms = [code.lower()] + [
            t.lower()
            for t in data.get("aliases", []) + [data.get("name_ja", ""), data.get("name_en", "")]
            if t
        ]
        if any(t in text for t in terms):
            targets.append(AvatarRef(code=code, name=data.get("name_ja", code)))
    return targets


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
    mapping = {
        "appearance_tags": "appearance",
        "mood_tags": "style",
        "color_tags": "color",
        "outfit_tags": "outfit_type",
    }
    for section, dim in mapping.items():
        for key, data in aliases.get(section, {}).items():
            name_ja = data.get("name_ja")
            terms = [
                _norm(t) for t in data.get("aliases", []) + ([name_ja] if name_ja else []) if t
            ]
            if any(t in text for t in terms):
                res[dim].append(name_ja or key)
    features = {"PhysBone": ["physbone", "pb"], "Modular Avatar": ["modular avatar", "ma"]}
    for f, keywords in features.items():
        if any(k in text for k in keywords):
            res["feature"].append(f)
    return TagSet(**res)
