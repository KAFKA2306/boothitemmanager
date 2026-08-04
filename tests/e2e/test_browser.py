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


def wait_for_catalogue(page: Page) -> None:
    expect(page.locator("#splash")).to_be_hidden(timeout=10000)
    expect(page.locator("#status-text")).to_contain_text("CONNECTED", timeout=20000)
    expect(page.locator(".asset-card").first).to_be_visible(timeout=10000)


def test_smoke_initialization(page: Page):
    js_errors = []
    page.on("pageerror", lambda err: js_errors.append(err.message))

    response = page.goto("http://localhost:8080/")
    assert response.status == 200
    wait_for_catalogue(page)
    assert len(js_errors) == 0, f"JS errors found: {js_errors}"

    expect(page.locator("#search-bar")).to_be_visible()
    expect(page.locator(".ux-skip-link")).to_be_attached()

    all_count = page.locator("#count-all")
    expect(all_count).not_to_have_text("0", timeout=5000)
    count_text = all_count.inner_text().replace(",", "")
    assert int(count_text) > 0


def test_data_load_integrity(page: Page):
    page.goto("http://localhost:8080/")
    status_text = page.locator("#status-text")
    expect(status_text).to_contain_text("CONNECTED", timeout=20000)
    expect(status_text).to_contain_text("40,0", timeout=20000)


def test_filter_generation(page: Page):
    page.goto("http://localhost:8080/")
    wait_for_catalogue(page)

    categories = ["avatar", "outfit", "accessory", "gimmick", "hair", "texture"]
    for category in categories:
        count_loc = page.locator(f"#count-{category}")
        count_text = count_loc.inner_text().replace(",", "")
        assert count_text != "", f"Category {category} count is empty"
        assert int(count_text) > 0, f"Category {category} should have > 0 items, got {count_text}"


def test_ui_rendering_and_modal(page: Page):
    page.goto("http://localhost:8080/")
    wait_for_catalogue(page)

    first_card = page.locator(".asset-card").first
    expect(first_card).to_be_visible()
    expect(first_card.locator(".asset-provenance")).to_be_visible()
    first_card.locator("[data-open-detail]").click()

    modal = page.locator("#detail-dialog")
    expect(modal).to_be_visible()
    expect(page.locator("#modal-title")).not_to_be_empty()
    expect(page.locator(".ux-provenance-section")).to_be_visible()
    expect(page.get_by_text("販売ページ観測", exact=True)).to_be_visible()

    page.locator("#modal-close-btn").click()
    expect(modal).to_be_hidden()


def test_search_functionality_and_url_restore(page: Page):
    page.goto("http://localhost:8080/")
    wait_for_catalogue(page)

    search_bar = page.locator("#search-bar")
    search_bar.fill("桔梗")
    page.wait_for_timeout(500)

    expect(page.locator(".ux-results-summary")).to_contain_text("条件で絞り込み")
    expect(page.locator(".asset-card").first).to_be_visible()
    expect(page).to_have_url(lambda url: "q=%E6%A1%94%E6%A2%97" in url)

    restored_url = page.url
    page.reload()
    wait_for_catalogue(page)
    expect(page.locator("#search-bar")).to_have_value("桔梗")
    assert page.url == restored_url


def test_compare_two_products_and_restore_selection(page: Page):
    page.goto("http://localhost:8080/")
    wait_for_catalogue(page)

    cards = page.locator(".asset-card")
    expect(cards).to_have_count(40)
    cards.nth(0).locator("[data-compare-item]").check()
    cards.nth(1).locator("[data-compare-item]").check()

    tray = page.locator("#ux-compare-tray")
    expect(tray).to_be_visible()
    expect(tray.locator("[data-compare-count]")).to_have_text("2")
    expect(page).to_have_url(lambda url: "compare=" in url)

    tray.locator("[data-show-comparison]").click()
    panel = page.locator("#ux-comparison-panel")
    expect(panel).to_be_visible()
    expect(panel.locator(".ux-comparison-table")).to_be_attached()
    expect(panel).to_contain_text("明示対応")
    expect(panel).to_contain_text("正規化タグ")

    compare_url = page.url
    page.reload()
    wait_for_catalogue(page)
    expect(page.locator("#ux-compare-tray [data-compare-count]")).to_have_text("2")
    assert page.url == compare_url


def test_mobile_filter_dialog(page: Page):
    page.set_viewport_size({"width": 375, "height": 812})
    page.goto("http://localhost:8080/")
    wait_for_catalogue(page)

    open_filter = page.locator(".ux-filter-open")
    expect(open_filter).to_be_visible()
    open_filter.click()
    dialog = page.locator("#ux-filter-dialog")
    expect(dialog).to_be_visible()
    expect(dialog.locator("#category-selector")).to_be_visible()
    dialog.locator("[data-filter-apply]").click()
    expect(dialog).to_be_hidden()

    expect(page.locator(".asset-card").first).to_be_visible()
    assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")


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
