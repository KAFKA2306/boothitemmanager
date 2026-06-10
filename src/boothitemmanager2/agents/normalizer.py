from bs4 import BeautifulSoup
import re
import json
import yaml
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
from urllib.parse import urljoin, urlparse
from ..core import TestBlock
from ..schemas.storage import RawAssetPage, Item, ItemCategory, AvatarRef, FileAsset


def _pick_like_count(soup: BeautifulSoup) -> int:
    elem = soup.select_one('[data-wishlist-count]')
    if elem and elem.get('data-wishlist-count'):
        try:
            return int(elem.get('data-wishlist-count'))
        except: pass
    button = soup.select_one('.wish-list-button')
    if button:
        count_text = button.get_text(strip=True)
        match = re.search(r'(\d+)', count_text)
        if match: return int(match.group(1))
    return 0

def _pick_published_at(soup: BeautifulSoup, json_ld: Optional[Dict[str, Any]]) -> Optional[datetime]:
    if json_ld and json_ld.get('releaseDate'):
        try:
            return datetime.fromisoformat(json_ld['releaseDate'].replace('Z', '+00:00'))
        except: pass
    
    date_elem = soup.select_one('.base-datetime')
    if date_elem:
        date_str = date_elem.get_text(strip=True)
        try:
            return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
        except: pass

    time_tag = soup.find('time')
    if time_tag and time_tag.get('datetime'):
        try:
            return datetime.fromisoformat(time_tag['datetime'].replace('Z', '+00:00'))
        except: pass

    return None

def _extract_tech_tags(title: str, description: Optional[str], tags: List[str]) -> List[str]:
    tech_tags = []
    full_text = f"{title} {description or ''} {' '.join(tags)}"
    keywords = {
        "Modular Avatar": ["Modular Avatar", "MA対応", "ModularAvatar"],
        "PhysBone": ["PhysBone", "PB対応", "Phys Bones"],
        "lilToon": ["lilToon", "リルトゥーン"],
        "Quest": ["Quest対応", "Quest版"]
    }
    for label, patterns in keywords.items():
        if any(p.lower() in full_text.lower() for p in patterns):
            tech_tags.append(label)
    return tech_tags

def normalize_html(raw_page: RawAssetPage, trace_id: str) -> TestBlock:
    """
    Normalizes HTML content from RawAssetPage into an Item model.
    Crash-Driven: No try-catch blocks.
    Zero-Fat: Focused on extraction logic.
    Schema: BoothItemManager2 Item (title/creator_name/category/tags_raw/thumbnail_url/targets/files).
    """
    pre_state: Dict[str, Any] = {
        "url": raw_page.url,
        "scraped_at": raw_page.scraped_at.isoformat()
    }

    soup = BeautifulSoup(raw_page.content, 'html.parser')

    # Extract item_id from URL
    item_id_match = re.search(r'items/(\d+)', raw_page.url)
    if not item_id_match:
        raise ValueError(f"Could not extract item_id from URL: {raw_page.url}")
    item_id = item_id_match.group(1)

    aliases = load_aliases()
    og_data = _parse_og_tags(soup)
    json_ld = _parse_json_ld(soup)

    title = _pick_name(soup, og_data)
    creator_name = _pick_shop_name(soup, og_data)
    creator_id = _pick_creator_id(soup, raw_page.url)
    price = _pick_price(soup, og_data, json_ld)
    thumbnail_url = _pick_image(soup, og_data, raw_page.url)
    description = _pick_description(soup, og_data)
    tags_raw = _pick_tags(soup)
    
    # Restored logic
    targets = pick_targets(title, description, tags_raw, aliases)
    category = infer_category(title, description, tags_raw, targets, aliases)
    tags_generated = extract_mood_tags(title, description, tags_raw, aliases)
    tech_tags = _extract_tech_tags(title, description, tags_raw)
    tags_generated.extend(tech_tags)
    
    files = _pick_files(soup)
    like_count = _pick_like_count(soup)
    published_at = _pick_published_at(soup, json_ld)

    item = Item(
        item_id=item_id,
        source="booth",
        source_url=raw_page.url,
        title=title,
        description=description or "",
        thumbnail_url=thumbnail_url or "",
        creator_id=creator_id or "unknown",
        creator_name=creator_name,
        published_at=published_at,
        tags_raw=tags_raw,
        tags_generated=tags_generated,
        category=category,
        like_count=like_count,
        price=price,
        targets=targets,
        files=files
    )

    actual_state: Dict[str, Any] = {"item": item}

    return TestBlock(
        trace_id=trace_id,
        input=raw_page.url,
        pre_state=pre_state,
        action="normalize_html",
        expected_state={"item_id": item_id},
        actual_state=actual_state,
        diff={},
        result="SUCCESS"
    )



def load_aliases() -> Dict[str, Any]:
    path = os.path.join(os.getcwd(), 'aliases.yml')
    if not os.path.exists(path):
        return {"avatars": {}, "types": {}}
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def _parse_og_tags(soup: BeautifulSoup) -> Dict[str, str]:
    og_data = {}
    for tag in soup.find_all('meta', property=lambda x: x and x.startswith('og:')):
        property_name = tag.get('property', '')[3:]
        content = tag.get('content')
        if property_name and content:
            og_data[property_name] = content
    return og_data


def _parse_json_ld(soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
    for script in soup.find_all('script', type='application/ld+json'):
        if script.string:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict): return data
                if isinstance(data, list) and data: return data[0]
            except: pass
    return None


def _pick_name(soup: BeautifulSoup, og_data: Dict[str, str]) -> str:
    if og_data.get('title'): return og_data['title'].strip()
    selectors = ['h1.item-name', 'h1.u-tpg-title1', 'h1[itemprop="name"]']
    for s in selectors:
        elem = soup.select_one(s)
        if elem: return elem.get_text(strip=True)
    raise ValueError("Could not extract item name")


def _pick_shop_name(soup: BeautifulSoup, og_data: Dict[str, str]) -> str:
    selectors = ['div.shop-name', 'a.shop-name', 'div.u-text-ellipsis > a', '.booth-user-name a', 'a[itemprop="author"]']
    for s in selectors:
        elem = soup.select_one(s)
        if elem: return elem.get_text(strip=True)
    if og_data.get('site_name'): return og_data['site_name']
    return "Unknown Shop"


def _pick_creator_id(soup: BeautifulSoup, url: str) -> Optional[str]:
    elem = soup.select_one('[data-product-brand]')
    if elem and elem.get('data-product-brand'):
        return elem.get('data-product-brand')
    selectors = ['a.shop-name', 'div.u-text-ellipsis > a', '.booth-user-name a']
    for s in selectors:
        elem = soup.select_one(s)
        if elem and elem.get('href'):
            href = elem.get('href')
            match = re.search(r'https://([^.]+)\.booth\.pm', href)
            if match: return match.group(1)
            match = re.search(r'/shop/([^/?]+)', href)
            if match: return match.group(1)
    parsed = urlparse(url)
    if parsed.hostname and parsed.hostname.endswith('.booth.pm'):
        sub = parsed.hostname.split('.')[0]
        if sub != 'booth': return sub
    return None


def _pick_price(soup: BeautifulSoup, og_data: Dict[str, str], json_ld: Optional[Dict[str, Any]]) -> Optional[int]:
    if json_ld:
        offers = json_ld.get('offers')
        if isinstance(offers, dict) and offers.get('price') is not None:
            return int(float(str(offers['price']).replace(',', '')))
    og_price = og_data.get('price:amount')
    if og_price:
        return int(float(str(og_price).replace(',', '')))
    price_elem = soup.select_one('.price .yen')
    if price_elem:
        match = re.search(r'([\d,]+)', price_elem.get_text())
        if match: return int(match.group(1).replace(',', ''))
    return None


def _pick_image(soup: BeautifulSoup, og_data: Dict[str, str], base_url: str) -> Optional[str]:
    img_url = og_data.get('image')
    if not img_url:
        img_elem = soup.select_one('img.market-item-image')
        if img_elem: img_url = img_elem.get('src')
    if img_url:
        full_url = urljoin(base_url, img_url)
        return re.sub(r'/c/\d+x\d+/', '/', full_url)
    return None


def _pick_description(soup: BeautifulSoup, og_data: Dict[str, str]) -> Optional[str]:
    desc = og_data.get('description')
    elem = soup.select_one('.item-description, .description, .js-market-item-detail-description')
    if elem:
        desc = elem.get_text('\n', strip=True)
    return desc or None


def _pick_tags(soup: BeautifulSoup) -> List[str]:
    tags = []
    for elem in soup.select('a.l-tag, a.u-tpg-label, .item-tags a, .item-card__badge a, .l-item-card-badge a'):
        tag_text = elem.get_text(strip=True).replace('#', '')
        if tag_text and tag_text not in tags:
            tags.append(tag_text)
    if not tags:
        desc_elem = soup.select_one('.item-description, .description, .js-market-item-detail-description')
        if desc_elem:
            text = desc_elem.get_text()
            found = re.findall(r'#([^\s#]+)', text)
            for t in found:
                if t not in tags: tags.append(t)
    return tags

def _pick_files(soup: BeautifulSoup) -> List[FileAsset]:
    files = []
    selectors = ['.download-item-name', '.variation-item .u-tpg-caption1', '.sheet-header', '.item-download-file-name', '.variation-name']
    for s in selectors:
        for elem in soup.select(s):
            name = elem.get_text(strip=True)
            if name and name not in ["ダウンロード商品", "在庫あり", "注文完了後ダウンロード可能"]:
                if not any(f.filename == name for f in files):
                    files.append(FileAsset(filename=name))
    if not files:
        btn = soup.select_one('button[data-product-name]')
        if btn:
            name = btn.get('data-product-name')
            if name: files.append(FileAsset(filename=name))
    return files

def pick_targets(name: str, description: Optional[str], tags: List[str], aliases: Dict[str, Any]) -> List[AvatarRef]:
    targets = []
    full_text = f"{name} {description or ''} {' '.join(tags)}".lower()
    avatars = aliases.get('avatars', {})
    for code, data in avatars.items():
        search_terms = data.get('aliases', []) + [data.get('name_ja', ''), data.get('name_en', '')]
        search_terms = [t.lower() for t in search_terms if t]
        if any(term in full_text for term in search_terms):
            targets.append(AvatarRef(code=code, name=data.get('name_ja', code)))
    return targets

def infer_category(name: str, description: Optional[str], tags: List[str], targets: List[AvatarRef], aliases: Dict[str, Any]) -> ItemCategory:
    full_text = f"{name} {description or ''} {' '.join(tags)}".lower()
    types_map = aliases.get('types', {})

    # 1. Multiple targets strongly implies a costume or accessory
    if len(targets) > 1:
        acc_aliases = types_map.get('accessory', {}).get('aliases', [])
        if any(term.lower() in full_text for term in acc_aliases):
            return ItemCategory.ACCESSORY
        return ItemCategory.OUTFIT

    # 2. Contextual indicators
    for type_code, category in [('costume', ItemCategory.OUTFIT), ('accessory', ItemCategory.ACCESSORY)]:
        data = types_map.get(type_code, {})
        indicators = data.get('indicators', [])
        for target in targets:
            for ind in indicators:
                pattern = rf"{re.escape(target.name)}[の\s]*{re.escape(ind)}"
                if re.search(pattern, f"{name} {description or ''}"):
                    return category

    # 3. Direct aliases
    mapping = {
        'avatar': ItemCategory.AVATAR,
        'costume': ItemCategory.OUTFIT,
        'accessory': ItemCategory.ACCESSORY,
        'gimmick': ItemCategory.GIMMICK,
        'tool': ItemCategory.GIMMICK,
    }
    for type_code, cat in mapping.items():
        data = types_map.get(type_code, {})
        if any(term.lower() in full_text for term in data.get('aliases', [])):
            return cat

    if any(k in full_text for k in ["アバター", "avatar"]):
        return ItemCategory.AVATAR
    return ItemCategory.OTHER


import unicodedata

def extract_mood_tags(title: str, description: Optional[str], tags: List[str], aliases: Dict[str, Any]) -> List[str]:
    """
    Extracts high-dimensional discovery tags (mood, outfit, color, etc.) from text.
    Severe: Uses NFKC normalization and checks all configured tag dimensions.
    """
    def _norm(t: str) -> str:
        return unicodedata.normalize('NFKC', t).lower()

    full_text = _norm(f"{title} {description or ''} {' '.join(tags)}")
    
    # Dimensions to extract
    sections = ['mood_tags', 'outfit_tags', 'color_tags', 'appearance_tags']
    extracted = []
    
    for section in sections:
        tag_map = aliases.get(section, {})
        for data in tag_map.values():
            name_ja = data.get('name_ja')
            if not name_ja: continue
            
            aliases_list = data.get('aliases', [])
            if any(_norm(term) in full_text for term in aliases_list):
                if name_ja not in extracted:
                    extracted.append(name_ja)
    
    return extracted
