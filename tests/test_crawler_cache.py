from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from boothitemmanager2 import crawler  # noqa: E402


class FakeSession:
    def __init__(self, *, response=None, error: Exception | None = None):
        self.response = response
        self.error = error
        self.calls = 0

    def get(self, *args, **kwargs):
        self.calls += 1
        if self.error:
            raise self.error
        return self.response


def test_fresh_cache_skips_network(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "input/raw/123.html"
    path.parent.mkdir(parents=True)
    path.write_text("cached", encoding="utf-8")
    monkeypatch.setattr(crawler, "DEFAULT_REQUEST_DELAY_SECONDS", 0)
    monkeypatch.setattr(
        crawler, "_session", lambda: (_ for _ in ()).throw(AssertionError("network"))
    )

    block = crawler.fetch_html("https://booth.pm/ja/items/123", "t", cache_ttl_seconds=3600)
    assert block.result == "SUCCESS"
    assert block.actual_state["cache"] == "fresh"
    assert block.actual_state["raw_page"].content == "cached"


def test_stale_cache_is_revalidated_atomically(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "input/raw/123.html"
    path.parent.mkdir(parents=True)
    path.write_text("old", encoding="utf-8")
    session = FakeSession(response=SimpleNamespace(status_code=200, text="new"))
    monkeypatch.setattr(crawler, "DEFAULT_REQUEST_DELAY_SECONDS", 0)
    monkeypatch.setattr(crawler, "_session", lambda: session)

    block = crawler.fetch_html("https://booth.pm/ja/items/123", "t", cache_ttl_seconds=0)
    assert block.result == "SUCCESS"
    assert session.calls == 1
    assert path.read_text(encoding="utf-8") == "new"
    assert not list(path.parent.glob("*.tmp-*"))


def test_failed_revalidation_preserves_last_known_good(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "input/raw/123.html"
    path.parent.mkdir(parents=True)
    path.write_text("known-good", encoding="utf-8")
    session = FakeSession(error=requests.ConnectionError("offline"))
    monkeypatch.setattr(crawler, "DEFAULT_REQUEST_DELAY_SECONDS", 0)
    monkeypatch.setattr(crawler, "_session", lambda: session)

    block = crawler.fetch_html("https://booth.pm/ja/items/123", "t", cache_ttl_seconds=0)
    assert block.result == "FAIL"
    assert block.actual_state["fallback_used"] is True
    assert block.actual_state["raw_page"].content == "known-good"
    assert path.read_text(encoding="utf-8") == "known-good"


def test_network_failure_without_cache_returns_fail_block(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    session = FakeSession(error=requests.ConnectionError("offline"))
    monkeypatch.setattr(crawler, "DEFAULT_REQUEST_DELAY_SECONDS", 0)
    monkeypatch.setattr(crawler, "_session", lambda: session)

    block = crawler.fetch_html("https://booth.pm/ja/items/123", "t", cache_ttl_seconds=0)
    assert block.result == "FAIL"
    assert block.actual_state["cache"] == "miss"
    assert block.actual_state["content_length"] == 0
