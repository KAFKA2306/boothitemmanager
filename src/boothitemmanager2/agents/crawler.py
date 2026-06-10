import requests
from datetime import datetime
from typing import Dict, Any
from ..core import TestBlock
from ..schemas.storage import RawAssetPage

def fetch_html(url: str, trace_id: str) -> TestBlock:
    """
    Fetches BOOTH product page HTML and returns it as a RawAssetPage wrapped in a TestBlock.
    Crash-Driven: No try-catch blocks. Exceptions are handled by the caller or retry mechanism.
    Zero-Fat: Minimal implementation focusing on the core task.
    """
    pre_state: Dict[str, Any] = {
        "url": url,
        "requested_at": datetime.now().isoformat()
    }
    
    _HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "ja,en;q=0.9",
    }

    response = requests.get(url, headers=_HEADERS, timeout=30)

    response.raise_for_status()
    
    raw_page = RawAssetPage(
        url=url,
        content=response.text,
        scraped_at=datetime.now()
    )
    
    # 3. Rawデータ蓄積 (Raw Data Accumulation)
    # Extract item_id from URL (e.g., https://booth.pm/ja/items/12345)
    import re
    from pathlib import Path
    item_id_match = re.search(r'items/(\d+)', url)
    save_path = None
    saved = False
    if item_id_match:
        item_id = item_id_match.group(1)
        storage_dir = Path("input/raw")
        storage_dir.mkdir(parents=True, exist_ok=True)
        save_path = storage_dir / f"{item_id}.html"
        save_path.write_text(response.text, encoding='utf-8')
        saved = True

    actual_state: Dict[str, Any] = {
        "raw_page": raw_page,
        "status_code": response.status_code,
        "content_length": len(response.text),
        "save_path": str(save_path) if save_path else None,
        "saved": saved
    }
    
    return TestBlock(
        trace_id=trace_id,
        input=url,
        pre_state=pre_state,
        action="fetch_html",
        expected_state={"status_code": 200},
        actual_state=actual_state,
        diff={},
        result="SUCCESS"
    )
