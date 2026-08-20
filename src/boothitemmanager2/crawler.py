from __future__ import annotations

import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from .core import TestBlock
from .storage import RawAssetPage

DEFAULT_CACHE_TTL_SECONDS = int(os.environ.get("BOOTH_CACHE_TTL_SECONDS", "21600"))
DEFAULT_REQUEST_DELAY_SECONDS = float(os.environ.get("BOOTH_REQUEST_DELAY_SECONDS", "1.25"))
DEFAULT_TIMEOUT_SECONDS = float(os.environ.get("BOOTH_REQUEST_TIMEOUT_SECONDS", "20"))

_HEADERS = {
    "User-Agent": "BoothItemManager2/1.0 (+https://github.com/KAFKA2306/boothitemmanager)",
    "Accept-Language": "ja,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml",
}


def _session() -> requests.Session:
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
    session.mount("http://", HTTPAdapter(max_retries=retry))
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers.update(_HEADERS)
    return session


def _cached_page(url: str, save_path: Path) -> RawAssetPage:
    content = save_path.read_text(encoding="utf-8")
    return RawAssetPage(
        url=url,
        content=content,
        scraped_at=datetime.fromtimestamp(save_path.stat().st_mtime, tz=timezone.utc),
    )


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def fetch_html(
    url: str,
    trace_id: str,
    *,
    cache_ttl_seconds: int | None = None,
    force_refresh: bool = False,
) -> TestBlock:
    """Fetch a BOOTH item page with bounded cache reuse and last-known-good fallback.

    A cache file is reusable only while it is younger than the configured TTL. Stale
    files are revalidated with a network GET. Failed refreshes never overwrite a known
    good page.
    """

    now = datetime.now(timezone.utc)
    pre_state: dict[str, Any] = {"url": url, "requested_at": now.isoformat()}
    item_id_match = re.search(r"items/(\d+)", url)
    item_id = item_id_match.group(1) if item_id_match else None
    save_path = Path("input/raw") / f"{item_id}.html" if item_id else None
    ttl = DEFAULT_CACHE_TTL_SECONDS if cache_ttl_seconds is None else max(0, cache_ttl_seconds)

    if save_path and save_path.exists() and not force_refresh:
        age = max(0.0, time.time() - save_path.stat().st_mtime)
        if age <= ttl:
            raw_page = _cached_page(url, save_path)
            return TestBlock(
                trace_id=trace_id,
                input=url,
                pre_state=pre_state,
                action="fetch_html",
                expected_state={"status_code": 200},
                actual_state={
                    "raw_page": raw_page,
                    "status_code": 200,
                    "content_length": len(raw_page.content),
                    "save_path": str(save_path),
                    "saved": False,
                    "cache": "fresh",
                    "fallback_used": False,
                },
                diff={},
                result="SUCCESS",
            )

    if DEFAULT_REQUEST_DELAY_SECONDS > 0:
        time.sleep(DEFAULT_REQUEST_DELAY_SECONDS)

    try:
        response = _session().get(
            url,
            timeout=(min(DEFAULT_TIMEOUT_SECONDS, 5.0), DEFAULT_TIMEOUT_SECONDS),
            allow_redirects=True,
        )
    except requests.RequestException as exc:
        if save_path and save_path.exists():
            raw_page = _cached_page(url, save_path)
            return TestBlock(
                trace_id=trace_id,
                input=url,
                pre_state=pre_state,
                action="fetch_html",
                expected_state={"status_code": 200},
                actual_state={
                    "raw_page": raw_page,
                    "status_code": None,
                    "content_length": len(raw_page.content),
                    "save_path": str(save_path),
                    "saved": False,
                    "cache": "stale",
                    "fallback_used": True,
                    "error": exc.__class__.__name__,
                },
                diff={},
                result="FAIL",
            )
        raw_page = RawAssetPage(url=url, content="", scraped_at=now)
        return TestBlock(
            trace_id=trace_id,
            input=url,
            pre_state=pre_state,
            action="fetch_html",
            expected_state={"status_code": 200},
            actual_state={
                "raw_page": raw_page,
                "status_code": None,
                "content_length": 0,
                "save_path": str(save_path) if save_path else None,
                "saved": False,
                "cache": "miss",
                "fallback_used": False,
                "error": exc.__class__.__name__,
            },
            diff={},
            result="FAIL",
        )

    if response.status_code == 200:
        raw_page = RawAssetPage(url=url, content=response.text, scraped_at=now)
        saved = False
        if save_path:
            _atomic_write(save_path, response.text)
            saved = True
        return TestBlock(
            trace_id=trace_id,
            input=url,
            pre_state=pre_state,
            action="fetch_html",
            expected_state={"status_code": 200},
            actual_state={
                "raw_page": raw_page,
                "status_code": response.status_code,
                "content_length": len(response.text),
                "save_path": str(save_path) if save_path else None,
                "saved": saved,
                "cache": "refreshed",
                "fallback_used": False,
            },
            diff={},
            result="SUCCESS",
        )

    if save_path and save_path.exists():
        raw_page = _cached_page(url, save_path)
        return TestBlock(
            trace_id=trace_id,
            input=url,
            pre_state=pre_state,
            action="fetch_html",
            expected_state={"status_code": 200},
            actual_state={
                "raw_page": raw_page,
                "status_code": response.status_code,
                "content_length": len(raw_page.content),
                "save_path": str(save_path),
                "saved": False,
                "cache": "stale",
                "fallback_used": True,
            },
            diff={},
            result="FAIL",
        )

    raw_page = RawAssetPage(url=url, content=response.text, scraped_at=now)
    return TestBlock(
        trace_id=trace_id,
        input=url,
        pre_state=pre_state,
        action="fetch_html",
        expected_state={"status_code": 200},
        actual_state={
            "raw_page": raw_page,
            "status_code": response.status_code,
            "content_length": len(response.text),
            "save_path": str(save_path) if save_path else None,
            "saved": False,
            "cache": "miss",
            "fallback_used": False,
        },
        diff={},
        result="FAIL",
    )
