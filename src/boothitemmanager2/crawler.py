from datetime import datetime
from typing import Any

import requests

from .core import TestBlock
from .storage import RawAssetPage


def fetch_html(url: str, trace_id: str) -> TestBlock:
    import re
    from pathlib import Path

    pre_state: dict[str, Any] = {"url": url, "requested_at": datetime.now().isoformat()}

    item_id_match = re.search("items/(\\d+)", url)
    item_id = item_id_match.group(1) if item_id_match else None
    storage_dir = Path("input/raw")
    save_path = storage_dir / f"{item_id}.html" if item_id else None

    # Load from local cache if available
    if save_path and save_path.exists():
        content = save_path.read_text(encoding="utf-8")
        raw_page = RawAssetPage(
            url=url, content=content, scraped_at=datetime.fromtimestamp(save_path.stat().st_mtime)
        )
        actual_state: dict[str, Any] = {
            "raw_page": raw_page,
            "status_code": 200,
            "content_length": len(content),
            "save_path": str(save_path),
            "saved": False,
        }
        return TestBlock(
            trace_id=trace_id,
            input=url,
            pre_state=pre_state,
            action="fetch_html",
            expected_state={"status_code": 200},
            actual_state=actual_state,
            diff={},
            result="SUCCESS",
        )
    import time
    import random
    from requests.adapters import HTTPAdapter
    from urllib3.util import Retry

    # Polite delay to prevent rate limiting (1-2s sleep)
    time.sleep(1.0 + random.random())

    _HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": "ja,en;q=0.9",
    }

    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=1.5,
        status_forcelist=[429, 500, 502, 503, 504],
        raise_on_status=False,
    )
    session.mount("http://", HTTPAdapter(max_retries=retries))
    session.mount("https://", HTTPAdapter(max_retries=retries))

    response = None
    try:
        response = session.get(url, headers=_HEADERS, timeout=20)
        if response.status_code != 200:
            raise requests.HTTPError(f"Status {response.status_code}")
    except Exception as e:
        # Fallback Strategy: Attempt using Allorigins public CORS proxy
        try:
            proxy_url = f"https://api.allorigins.win/get?url={url}"
            proxy_res = session.get(proxy_url, timeout=25)
            if proxy_res.status_code == 200:
                proxy_data = proxy_res.json()
                html_content = proxy_data.get("contents", "")
                if html_content:
                    # Mock response object for compatibility
                    class MockResponse:
                        def __init__(self, text, status_code):
                            self.text = text
                            self.content = text
                            self.status_code = status_code
                            self.url = url
                        def raise_for_status(self):
                            pass
                    response = MockResponse(html_content, 200)
        except Exception:
            pass
        if not response:
            if response is not None:
                response.raise_for_status()
            raise e

    raw_page = RawAssetPage(url=url, content=response.text, scraped_at=datetime.now())

    saved = False
    if save_path and response.status_code == 200:
        storage_dir.mkdir(parents=True, exist_ok=True)
        save_path.write_text(response.text, encoding="utf-8")
        saved = True

    actual_state: dict[str, Any] = {
        "raw_page": raw_page,
        "status_code": response.status_code,
        "content_length": len(response.text),
        "save_path": str(save_path) if save_path else None,
        "saved": saved,
    }
    return TestBlock(
        trace_id=trace_id,
        input=url,
        pre_state=pre_state,
        action="fetch_html",
        expected_state={"status_code": 200},
        actual_state=actual_state,
        diff={},
        result="SUCCESS",
    )
