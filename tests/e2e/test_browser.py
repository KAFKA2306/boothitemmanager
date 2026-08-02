import subprocess
import time

import pytest
import requests
from playwright.sync_api import Page, expect


@pytest.fixture(scope="session", autouse=True)
def start_server():
    process = subprocess.Popen(["python3", "-m", "http.server", "8080", "--directory", "dist"])
    for _ in range(10):
        try:
            response = requests.get("http://localhost:8080/", timeout=2)
            if response.status_code == 200:
                break
        except requests.ConnectionError:
            pass
        time.sleep(0.5)
    else:
        process.terminate()
        pytest.fail("Could not start local server")

    yield "http://localhost:8080"
    process.terminate()


def test_smoke_initialization(page: Page):
    js_errors = []
    page.on("pageerror", lambda err: js_errors.append(err.message))

    response = page.goto("http://localhost:8080/")
    assert response.status == 200
    assert len(js_errors) == 0, f"JS errors found: {js_errors}"

    splash = page.locator("#splash")
    expect(splash).to_be_hidden(timeout=10000)
    expect(page.locator("#search-bar")).to_be_visible()

    all_count = page.locator("#count-all")
    expect(all_count).not_to_have_text("0", timeout=5000)
    count_text = all_count.inner_text().replace(",", "")
    assert int(count_text) > 0


def test_data_load_integrity(page: Page):
    page.goto("http://localhost:8080/")
    status_text = page.locator("#status-text")
    expect(status_text).to_contain_text("CONNECTED", timeout=15000)
    expect(status_text).to_contain_text("40,0", timeout=15000)


def test_filter_generation(page: Page):
    page.goto("http://localhost:8080/")
    expect(page.locator("#splash")).to_be_hidden(timeout=10000)
    expect(page.locator("#status-text")).to_contain_text("CONNECTED", timeout=15000)

    categories = ["avatar", "outfit", "accessory", "gimmick", "hair", "texture"]
    for category in categories:
        count_loc = page.locator(f"#count-{category}")
        count_text = count_loc.inner_text().replace(",", "")
        assert count_text != "", f"Category {category} count is empty"
        assert int(count_text) > 0, f"Category {category} should have > 0 items, got {count_text}"


def test_ui_rendering_and_modal(page: Page):
    page.goto("http://localhost:8080/")
    expect(page.locator("#splash")).to_be_hidden(timeout=10000)

    first_card = page.locator(".asset-card").first
    expect(first_card).to_be_visible()
    first_card.click()

    modal = page.locator("#detail-dialog")
    expect(modal).to_be_visible()
    expect(page.locator("#modal-title")).not_to_be_empty()

    page.locator("#modal-close-btn").click()
    expect(modal).to_be_hidden()


def test_search_functionality(page: Page):
    page.goto("http://localhost:8080/")
    expect(page.locator("#splash")).to_be_hidden(timeout=10000)

    search_bar = page.locator("#search-bar")
    search_bar.fill("桔梗")
    page.wait_for_timeout(500)

    meta = page.locator("#active-filters-row span")
    expect(meta).to_contain_text("items located")
    expect(page.locator(".asset-card").first).to_be_visible()


def test_ai_tool_evidence_page(page: Page):
    js_errors = []
    page.on("pageerror", lambda err: js_errors.append(err.message))

    response = page.goto("http://localhost:8080/ai-tools.html")
    assert response.status == 200
    expect(page.locator("#item-count")).to_have_text("9", timeout=5000)
    expect(page.locator("#shop-count")).to_have_text("7", timeout=5000)
    expect(page.locator(".card").first).to_be_visible()
    expect(page.get_by_text("ショップがAI関連ツールを販売していても")).to_be_visible()
    assert js_errors == []
