#!/usr/bin/env python3
"""Incrementally re-observe BOOTH listings and update only material catalogue changes.

The runner is intentionally stateless. Known items are partitioned deterministically
across schedule slots, while new listings are discovered from public BOOTH search pages.
No-op runs write only an untracked report, so they do not create commits or deployments.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from boothitemmanager2.freshness import (  # noqa: E402
    atomic_write_json,
    atomic_write_text,
    isoformat_utc,
    refresh_cycle_hours,
    stable_refresh_batch,
    utc_now,
)

BOOTH_ORIGIN = "https://booth.pm"
DEFAULT_DISCOVERY_URLS = ("https://booth.pm/ja/search/VRChat?sort=new",)
ITEM_RE = re.compile(r"^/ja/items/(\d+)(?:$|[?#])")
USER_AGENT = "BoothItemManager2/1.0 (+https://github.com/KAFKA2306/boothitemmanager)"


@dataclass
class Observation:
    item_id: str
    source_url: str
    status_code: int
    title: str | None = None
    description: str | None = None
    thumbnail: str | None = None
    price: int | None = None
    availability: str | None = None


def session_with_retries() -> requests.Session:
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        status=3,
        backoff_factor=1.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        respect_retry_after_header=True,
        raise_on_status=False,
    )
    session = requests.Session()
    adapter = HTTPAdapter(max_retries=retry, pool_connections=4, pool_maxsize=4)
    session.mount("https://", adapter)
    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept-Language": "ja,en;q=0.8",
            "Accept": "text/html,application/xhtml+xml",
        }
    )
    return session


def _json_ld_products(soup: BeautifulSoup) -> Iterable[dict[str, Any]]:
    for node in soup.select("script[type='application/ld+json']"):
        raw = node.string or node.get_text()
        if not raw.strip():
            continue
        try:
            value = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            continue
        values = value if isinstance(value, list) else [value]
        for candidate in values:
            if isinstance(candidate, dict) and candidate.get("@type") in {"Product", "IndividualProduct"}:
                yield candidate
            if isinstance(candidate, dict) and isinstance(candidate.get("@graph"), list):
                for nested in candidate["@graph"]:
                    if isinstance(nested, dict) and nested.get("@type") in {
                        "Product",
                        "IndividualProduct",
                    }:
                        yield nested


def _meta(
    soup: BeautifulSoup, *, property_name: str | None = None, name: str | None = None
) -> str | None:
    selector = None
    if property_name:
        selector = f'meta[property="{property_name}"]'
    elif name:
        selector = f'meta[name="{name}"]'
    if not selector:
        return None
    element = soup.select_one(selector)
    if not element:
        return None
    value = element.get("content")
    return str(value).strip() if value else None


def _price_from_product(product: dict[str, Any]) -> int | None:
    offers = product.get("offers")
    if isinstance(offers, list):
        offers = offers[0] if offers else None
    if not isinstance(offers, dict):
        return None
    raw = offers.get("price") or offers.get("lowPrice")
    try:
        return int(float(str(raw).replace(",", ""))) if raw is not None else None
    except ValueError:
        return None


def parse_item_page(item_id: str, url: str, html: str, status_code: int = 200) -> Observation:
    if status_code != 200:
        return Observation(item_id=item_id, source_url=url, status_code=status_code)

    soup = BeautifulSoup(html, "html.parser")
    product = next(iter(_json_ld_products(soup)), {})
    offers = product.get("offers") if isinstance(product, dict) else None
    if isinstance(offers, list):
        offers = offers[0] if offers else None

    title = product.get("name") or _meta(soup, property_name="og:title")
    description = _meta(soup, name="description") or product.get("description")
    thumbnail = _meta(soup, property_name="og:image")
    if not thumbnail:
        image = product.get("image")
        thumbnail = (
            image[0]
            if isinstance(image, list) and image
            else image
            if isinstance(image, str)
            else None
        )
    availability = offers.get("availability") if isinstance(offers, dict) else None

    return Observation(
        item_id=item_id,
        source_url=url,
        status_code=status_code,
        title=str(title).strip() if title else None,
        description=str(description).strip() if description else None,
        thumbnail=str(thumbnail).strip() if thumbnail else None,
        price=_price_from_product(product),
        availability=str(availability).strip() if availability else None,
    )


def discover_item_urls(html: str) -> dict[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    result: dict[str, str] = {}
    for link in soup.select("a[href]"):
        href = str(link.get("href") or "")
        if href.startswith(BOOTH_ORIGIN):
            href = href.removeprefix(BOOTH_ORIGIN)
        match = ITEM_RE.match(href)
        if not match:
            continue
        item_id = match.group(1)
        result[item_id] = f"{BOOTH_ORIGIN}/ja/items/{item_id}"
    return result


def _shard_number(path: Path) -> int:
    match = re.search(r"part(\d+)\.json$", path.name)
    if not match:
        raise ValueError(f"unexpected shard filename: {path}")
    return int(match.group(1))


def load_summary_shards(api_dir: Path) -> tuple[dict[int, list[dict[str, Any]]], dict[str, int]]:
    shards: dict[int, list[dict[str, Any]]] = {}
    location: dict[str, int] = {}
    paths = sorted(api_dir.glob("catalog_summary_part*.json"), key=_shard_number)
    if not paths:
        raise FileNotFoundError(f"no catalog summary shards under {api_dir}")
    for path in paths:
        number = _shard_number(path)
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError(f"{path} must contain a JSON array")
        shards[number] = data
        for item in data:
            item_id = str(item.get("id", ""))
            if not item_id:
                raise ValueError(f"{path} contains item without id")
            if item_id in location:
                raise ValueError(f"duplicate catalog id: {item_id}")
            location[item_id] = number
    return shards, location


def summary_for_new(obs: Observation, observed_at: str) -> dict[str, Any]:
    return {
        "id": obs.item_id,
        "title": obs.title or f"BOOTH item {obs.item_id}",
        "category": "ASSET",
        "price": obs.price,
        "like_count": 0,
        "compatible_avatars": [],
        "tags": [],
        "style": [],
        "outfit_type": [],
        "appearance": [],
        "color": [],
        "accessory": [],
        "body_type": [],
        "feature": [],
        "platform": [],
        "season": [],
        "has_dynamic_bone": False,
        "quest_compatible": False,
        "author": "Unknown Shop",
        "thumbnail": obs.thumbnail or "",
        "booth_url": obs.source_url,
        "source_status": "observed",
        "last_observed_at": observed_at,
        "last_changed_at": observed_at,
        "availability": obs.availability,
    }


def update_summary(current: dict[str, Any], obs: Observation, observed_at: str) -> bool:
    before = json.dumps(current, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if obs.status_code in {404, 410}:
        if current.get("source_status") != "unavailable":
            current["source_status"] = "unavailable"
            current["last_observed_at"] = observed_at
            current["last_changed_at"] = observed_at
    elif obs.status_code == 200:
        material = {
            "title": obs.title,
            "price": obs.price,
            "thumbnail": obs.thumbnail,
            "availability": obs.availability,
        }
        materially_changed = False
        for key, value in material.items():
            if value is not None and current.get(key) != value:
                current[key] = value
                materially_changed = True
        if current.get("source_status") != "observed":
            current["source_status"] = "observed"
            materially_changed = True
        if materially_changed:
            current["last_observed_at"] = observed_at
            current["last_changed_at"] = observed_at
    after = json.dumps(current, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return before != after


def _details_path(api_dir: Path, item_id: str) -> Path:
    shard = int(item_id) % 100 if item_id.isdigit() else sum(ord(char) for char in item_id) % 100
    return api_dir / "details" / f"shard_{shard:02}.json"


def update_detail(api_dir: Path, obs: Observation, observed_at: str) -> bool:
    path = _details_path(api_dir, obs.item_id)
    data: dict[str, Any] = {}
    if path.exists():
        loaded = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            data = loaded
    current = data.get(obs.item_id)
    if current is None:
        if obs.status_code != 200:
            return False
        current = {
            "item_id": obs.item_id,
            "source_url": obs.source_url,
            "title": obs.title or f"BOOTH item {obs.item_id}",
            "description": obs.description or "",
            "thumbnail_url": obs.thumbnail or "",
            "creator_id": "unknown",
            "creator_name": "Unknown Shop",
            "published_at": None,
            "like_count": 0,
            "price": obs.price,
            "category": "ASSET",
            "tag_set": {
                "appearance": [],
                "body_type": [],
                "style": [],
                "color": [],
                "outfit_type": [],
                "accessory": [],
                "feature": [],
                "platform": [],
                "season": [],
                "avatar_link": [],
                "material_property": [],
                "niche_subculture": [],
                "activity_scene": [],
            },
            "similar_items": [],
            "tags_raw": [],
            "targets": [],
            "files": [],
            "source": "booth",
            "audit_status": "UNVERIFIED",
            "source_status": "observed",
            "last_observed_at": observed_at,
            "last_changed_at": observed_at,
            "availability": obs.availability,
        }
        data[obs.item_id] = current
        atomic_write_json(path, data, compact=True)
        return True

    before = json.dumps(current, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if obs.status_code in {404, 410}:
        if current.get("source_status") != "unavailable":
            current["source_status"] = "unavailable"
            current["last_observed_at"] = observed_at
            current["last_changed_at"] = observed_at
    elif obs.status_code == 200:
        updates = {
            "title": obs.title,
            "description": obs.description,
            "thumbnail_url": obs.thumbnail,
            "price": obs.price,
            "availability": obs.availability,
        }
        material = False
        for key, value in updates.items():
            if value is not None and current.get(key) != value:
                current[key] = value
                material = True
        if current.get("source_status") != "observed":
            current["source_status"] = "observed"
            material = True
        if material:
            current["last_observed_at"] = observed_at
            current["last_changed_at"] = observed_at
    after = json.dumps(current, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if before == after:
        return False
    atomic_write_json(path, data, compact=True)
    return True


def write_summary_shard(api_dir: Path, number: int, rows: list[dict[str, Any]]) -> None:
    atomic_write_json(api_dir / f"catalog_summary_part{number}.json", rows, compact=True)
    js = f"window.BOOTH_CATALOG_PART{number} = " + json.dumps(
        rows, ensure_ascii=False, separators=(",", ":")
    ) + ";\n"
    atomic_write_text(api_dir / f"catalog_summary_part{number}.js", js)


def _load_metadata(api_dir: Path) -> dict[str, Any]:
    path = api_dir / "metadata.json"
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else {}


def _write_metadata(api_dir: Path, metadata: dict[str, Any]) -> None:
    atomic_write_json(api_dir / "metadata.json", metadata)
    atomic_write_text(
        api_dir / "metadata.js",
        "window.BOOTH_METADATA = "
        + json.dumps(metadata, ensure_ascii=False, separators=(",", ":"))
        + ";\n",
    )


def fetch(session: requests.Session, url: str, timeout: float) -> requests.Response:
    return session.get(url, timeout=(min(timeout, 5.0), timeout), allow_redirects=True)


def _summary_url(
    shards: dict[int, list[dict[str, Any]]], location: dict[str, int], item_id: str
) -> str:
    number = location[item_id]
    row = next(row for row in shards[number] if str(row.get("id")) == item_id)
    url = row.get("booth_url")
    return str(url) if url else f"{BOOTH_ORIGIN}/ja/items/{item_id}"


def run(
    *,
    api_dir: Path,
    discovery_urls: list[str],
    max_known: int,
    max_new: int,
    interval_minutes: int,
    request_interval: float,
    timeout: float,
    now: datetime,
    session: requests.Session | None = None,
    report_path: Path | None = None,
) -> dict[str, Any]:
    session = session or session_with_retries()
    observed_at = isoformat_utc(now)
    shards, location = load_summary_shards(api_dir)
    known_ids = set(location)
    discovered: dict[str, str] = {}
    discovery_errors: list[str] = []

    for url in discovery_urls:
        try:
            response = fetch(session, url, timeout)
            if response.status_code != 200:
                discovery_errors.append(f"{url}: HTTP {response.status_code}")
                continue
            discovered.update(discover_item_urls(response.text))
        except requests.RequestException as exc:
            discovery_errors.append(f"{url}: {exc.__class__.__name__}")
        if request_interval:
            time.sleep(request_interval)

    all_new_ids = sorted(set(discovered) - known_ids, key=int, reverse=True)
    new_ids = all_new_ids[:max_new]
    known_batch = stable_refresh_batch(
        known_ids,
        now=now,
        batch_size=max_known,
        interval_minutes=interval_minutes,
    )
    selected = [
        (item_id, discovered.get(item_id) or _summary_url(shards, location, item_id))
        for item_id in new_ids
    ]
    selected.extend((item_id, _summary_url(shards, location, item_id)) for item_id in known_batch)

    changed_ids: list[str] = []
    unavailable_ids: list[str] = []
    fetch_errors: list[str] = []
    successful_observations = 0
    touched_shards: set[int] = set()

    for item_id, url in selected:
        try:
            response = fetch(session, url, timeout)
        except requests.RequestException as exc:
            fetch_errors.append(f"{item_id}: {exc.__class__.__name__}")
            if request_interval:
                time.sleep(request_interval)
            continue
        obs = parse_item_page(item_id, url, response.text, response.status_code)
        if response.status_code not in {200, 404, 410}:
            fetch_errors.append(f"{item_id}: HTTP {response.status_code}")
            if request_interval:
                time.sleep(request_interval)
            continue
        successful_observations += 1
        if response.status_code in {404, 410}:
            unavailable_ids.append(item_id)

        if item_id in location:
            number = location[item_id]
            row = next(row for row in shards[number] if str(row.get("id")) == item_id)
            if update_summary(row, obs, observed_at):
                touched_shards.add(number)
                changed_ids.append(item_id)
            if update_detail(api_dir, obs, observed_at) and item_id not in changed_ids:
                changed_ids.append(item_id)
        elif response.status_code == 200:
            number = max(shards)
            if len(shards[number]) >= 5000:
                number += 1
                shards[number] = []
            shards[number].append(summary_for_new(obs, observed_at))
            location[item_id] = number
            touched_shards.add(number)
            update_detail(api_dir, obs, observed_at)
            changed_ids.append(item_id)

        if request_interval:
            time.sleep(request_interval)

    for number in sorted(touched_shards):
        write_summary_shard(api_dir, number, shards[number])

    total_items = sum(len(rows) for rows in shards.values())
    material_change = bool(changed_ids)
    if material_change:
        metadata = _load_metadata(api_dir)
        metadata["catalog_shards"] = len(shards)
        metadata["updated_at"] = observed_at
        _write_metadata(api_dir, metadata)
        atomic_write_json(
            api_dir / "freshness.json",
            {
                "schema_version": 1,
                "source": BOOTH_ORIGIN,
                "last_catalog_change_at": observed_at,
                "catalog_items": total_items,
                "changed_items": len(changed_ids),
                "new_items": len([item_id for item_id in changed_ids if item_id in new_ids]),
                "unavailable_items": len(unavailable_ids),
                "refresh_interval_minutes": interval_minutes,
                "known_item_refresh_cycle_hours": refresh_cycle_hours(
                    len(known_ids), max_known, interval_minutes
                ),
            },
        )

    report = {
        "schema_version": 1,
        "observed_at": observed_at,
        "catalog_items_before": len(known_ids),
        "selected_known_items": len(known_batch),
        "discovered_candidates": len(discovered),
        "new_candidates": len(all_new_ids),
        "new_candidates_processed": len(new_ids),
        "selected_items": len(selected),
        "successful_observations": successful_observations,
        "material_change": material_change,
        "changed_item_ids": changed_ids,
        "unavailable_item_ids": unavailable_ids,
        "discovery_errors": discovery_errors,
        "fetch_errors": fetch_errors,
        "known_item_refresh_cycle_hours": refresh_cycle_hours(
            len(known_ids), max_known, interval_minutes
        ),
    }
    if report_path:
        atomic_write_json(report_path, report)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-dir", type=Path, default=ROOT / "api")
    parser.add_argument(
        "--discovery-url",
        action="append",
        dest="discovery_urls",
        default=None,
        help="Public BOOTH listing/search URL. Repeatable.",
    )
    parser.add_argument(
        "--max-known", type=int, default=int(os.environ.get("MAX_KNOWN_PER_RUN", "120"))
    )
    parser.add_argument(
        "--max-new", type=int, default=int(os.environ.get("MAX_NEW_PER_RUN", "30"))
    )
    parser.add_argument("--interval-minutes", type=int, default=15)
    parser.add_argument(
        "--request-interval",
        type=float,
        default=float(os.environ.get("BOOTH_REQUEST_INTERVAL_SECONDS", "1.25")),
    )
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--report", type=Path, default=ROOT / "build" / "refresh-report.json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.max_known <= 0:
        raise SystemExit("--max-known must be positive")
    if args.max_new <= 0:
        raise SystemExit("--max-new must be positive")
    discovery_urls = args.discovery_urls or list(DEFAULT_DISCOVERY_URLS)
    report = run(
        api_dir=args.api_dir,
        discovery_urls=discovery_urls,
        max_known=args.max_known,
        max_new=args.max_new,
        interval_minutes=args.interval_minutes,
        request_interval=max(0.0, args.request_interval),
        timeout=args.timeout,
        now=utc_now(),
        report_path=args.report,
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    selected = report["selected_items"]
    successful = report["successful_observations"]
    fetch_error_rate = (len(report["fetch_errors"]) / selected) if selected else 0.0
    if report["discovery_errors"] or (selected and successful == 0) or fetch_error_rate > 0.20:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
