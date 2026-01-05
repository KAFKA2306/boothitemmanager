import json
import re
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

@dataclass
class ItemMetadata:
    item_id: int
    name: str | None = None
    shop_name: str | None = None
    creator_id: str | None = None
    image_url: str | None = None
    current_price: int | None = None
    description_excerpt: str | None = None
    canonical_path: str = None
    files: list = None
    scraped_at: str | None = None
    page_updated_at: str | None = None
    related_item_ids: list = None
    related_item_ids: list = None

    def __post_init__(self):
        if self.files is None: self.files = []
        if self.related_item_ids is None: self.related_item_ids = []
        if self.scraped_at is None: self.scraped_at = datetime.now().isoformat()
        if self.canonical_path is None: self.canonical_path = f"/ja/items/{self.item_id}"

class BoothScraper:
    def __init__(self, cache_file: str = "booth_item_cache.json", rate_limit: float = 1.0):
        self.cache_file = Path(cache_file)
        self.rate_limit = rate_limit
        self.last_request_time = 0
        self.cache = self._load_cache()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }

    def _load_cache(self) -> dict[str, dict[str, Any]]:
        if self.cache_file.exists():
            with open(self.cache_file, encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_cache(self):
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=2)

    def _rate_limit_wait(self):
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.rate_limit:
            time.sleep(self.rate_limit - time_since_last)
        self.last_request_time = time.time()

    def _parse_json_ld(self, soup: BeautifulSoup) -> dict[str, Any] | None:
        for script in soup.find_all("script", type="application/ld+json"):
            if script.string:
                data = json.loads(script.string)
                if isinstance(data, dict) and "@type" in data:
                    return data
                elif isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
                    return data[0]
        return None

    def _parse_og_tags(self, soup: BeautifulSoup) -> dict[str, str]:
        og_data = {}
        for tag in soup.find_all("meta", property=lambda x: x and x.startswith("og:")):
            property_name = tag.get("property", "")[3:]
            content = tag.get("content")
            if property_name and content:
                og_data[property_name] = content
        return og_data

    def _pick_name(self, soup: BeautifulSoup, og_data: dict[str, str]) -> str | None:
        if og_data.get("title"): return og_data["title"].strip()
        for selector in ["h1.item-name", "h1.u-tpg-title1", 'h1[itemprop="name"]', ".item-name h1", ".item-header h1"]:
            elem = soup.select_one(selector)
            if elem: return elem.get_text(strip=True)
        return None

    def _pick_shop_name(self, soup: BeautifulSoup, og_data: dict[str, str]) -> str | None:
        for selector in ["a.shop-name", "div.u-text-ellipsis > a", 'a[itemprop="author"]', ".shop-name"]:
            elem = soup.select_one(selector)
            if elem: return elem.get_text(strip=True)
        return og_data.get("site_name")

    def _pick_creator_id(self, soup: BeautifulSoup, response_url: str) -> str | None:
        for selector in ["a.shop-name", "div.u-text-ellipsis > a", 'a[itemprop="author"]']:
            elem = soup.select_one(selector)
            if elem:
                href = elem.get("href", "")
                if m := re.search(r"https://([^.]+)\.booth\.pm", href): return m.group(1)
                if m := re.search(r"/shop/([^/?]+)", href): return m.group(1)
        parsed_url = urlparse(response_url)
        if parsed_url.hostname and parsed_url.hostname.endswith(".booth.pm"):
            subdomain = parsed_url.hostname.split(".")[0]
            if subdomain != "booth": return subdomain
        return None

    def _pick_price(self, soup: BeautifulSoup, og_data: dict[str, str], json_ld: dict[str, Any] | None = None) -> int | None:
        if json_ld:
            offers = json_ld.get("offers")
            if offers:
                if isinstance(offers, dict):
                    if (price := offers.get("price")) is not None: return int(float(str(price).replace(",", "")))
                    if (low_price := offers.get("lowPrice")) is not None: return int(float(str(low_price).replace(",", "")))
                elif isinstance(offers, list) and len(offers) > 0:
                    if (price := offers[0].get("price")) is not None: return int(float(str(price).replace(",", "")))
        
        if (og_price := og_data.get("price:amount")):
            if m := re.search(r"[\d,]+", str(og_price)): return int(m.group().replace(",", ""))

        for selector in ["div.price", 'span[itemprop="price"]', ".price .yen", ".item-price .yen"]:
            elem = soup.select_one(selector)
            if elem:
                if m := re.search(r"¥\s*([\d,]+)", elem.get_text(strip=True)): return int(m.group(1).replace(",", ""))
        return None

    def _pick_image(self, soup: BeautifulSoup, og_data: dict[str, str], base_url: str) -> str | None:
        if og_data.get("image"): return self._normalize_image_quality(urljoin(base_url, og_data["image"]))
        return None

    def _pick_description(self, soup: BeautifulSoup, og_data: dict[str, str]) -> str | None:
        if og_data.get("description"): return og_data["description"].strip()[:200]
        for selector in [".item-description .markdown", ".item-description"]:
            elem = soup.select_one(selector)
            if elem: return elem.get_text(strip=True)[:200]
        return None

    def _pick_files(self, soup: BeautifulSoup) -> list[str]:
        files = []
        for selector in [".download-list .file-name", ".file-list .file-name"]:
            for elem in soup.select(selector):
                filename = elem.get_text(strip=True)
                if filename: files.append(filename)
        return files

    def _extract_related_item_ids(self, soup: BeautifulSoup) -> list[int]:
        related_ids = []
        for selector in [".item-description", ".related-items", ".markdown"]:
            elem = soup.select_one(selector)
            if elem:
                content_text = elem.get_text()
                for match in re.findall(r"items/(\d+)", content_text):
                    related_id = int(match)
                    if 1_000_000 <= related_id <= 99_999_999 and related_id not in related_ids:
                        related_ids.append(related_id)
                for link in elem.find_all("a", href=True):
                    href = link.get("href", "")
                    for match in re.findall(r"items/(\d+)", href):
                        related_id = int(match)
                        if 1_000_000 <= related_id <= 99_999_999 and related_id not in related_ids:
                            related_ids.append(related_id)
        return related_ids

    def _normalize_image_quality(self, url: str) -> str:
        if not url: return url
        if "booth.pximg.net" in url or "booth.pm" in url:
            normalized_url = re.sub(r"/c/\d+x\d+/", "/", url)
            return normalized_url
        return url

    def _extract_metadata(self, html: str, item_id: int, response_url: str) -> ItemMetadata:
        soup = BeautifulSoup(html, "html.parser")
        json_ld = self._parse_json_ld(soup)
        og_data = self._parse_og_tags(soup)
        
        page_updated_at = None
        if json_ld:
            date_modified = json_ld.get("dateModified") or json_ld.get("datePublished")
            if date_modified: page_updated_at = date_modified

        return ItemMetadata(
            item_id=item_id,
            name=self._pick_name(soup, og_data),
            shop_name=self._pick_shop_name(soup, og_data),
            creator_id=self._pick_creator_id(soup, response_url),
            image_url=self._pick_image(soup, og_data, response_url),
            current_price=self._pick_price(soup, og_data, json_ld),
            description_excerpt=self._pick_description(soup, og_data),
            canonical_path=f"/ja/items/{item_id}",
            files=self._pick_files(soup),
            page_updated_at=page_updated_at,
            related_item_ids=self._extract_related_item_ids(soup),
        )

    def scrape_item(self, item_id: int, force_refresh: bool = False) -> ItemMetadata:
        cache_key = str(item_id)
        if not force_refresh and cache_key in self.cache:
            cached_data = self.cache[cache_key].copy()
            if "canonical_url" in cached_data:
                canonical_url = cached_data.pop("canonical_url")
                if canonical_url:
                    parsed = urlparse(canonical_url)
                    cached_data["canonical_path"] = parsed.path
                else:
                    cached_data["canonical_path"] = f"/ja/items/{item_id}"
            if "page_updated_at" not in cached_data:
                cached_data["page_updated_at"] = cached_data.get("updated_at")
            if "related_item_ids" not in cached_data:
                cached_data["related_item_ids"] = []
            cached_data.pop("updated_at", None)
            return ItemMetadata(**cached_data)

        url = f"https://booth.pm/ja/items/{item_id}"
        self._rate_limit_wait()
        
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        metadata = self._extract_metadata(response.text, item_id, response.url)
        self.cache[cache_key] = asdict(metadata)
        self._save_cache()
        return metadata

    def scrape_items(self, item_ids: list, force_refresh: bool = False) -> dict[int, ItemMetadata]:
        results = {}
        for item_id in item_ids:
            results[item_id] = self.scrape_item(item_id, force_refresh)
        return results
