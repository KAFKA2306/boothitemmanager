import json
import re
import subprocess
import time
from pathlib import Path

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
    wait_for_catalogue(page)

    status = page.locator("#status-text").inner_text()
    match = re.fullmatch(r"CONNECTED \[([1-9][\d,]*)\]", status)
    assert match is not None, f"unexpected catalogue status: {status}"

    status_count = int(match.group(1).replace(",", ""))
    all_count = int(page.locator("#count-all").inner_text().replace(",", ""))
    assert status_count == all_count


def test_filter_generation(page: Page):
    page.goto("http://localhost:8080/")
    wait_for_catalogue(page)

    categories = ["avatar", "outfit", "accessory", "gimmick", "hair", "texture"]
    for category in categories:
        count_loc = page.locator(f"#count-{category}")
        count_text = count_loc.inner_text().replace(",", "")
        assert count_text != "", f"Category {category} count is empty"
        assert int(count_text) > 0, f"Category {category} should have > 0 items, got {count_text}"


def test_ui_rendering_modal_and_shared_detail_url(page: Page):
    page.goto("http://localhost:8080/")
    wait_for_catalogue(page)

    first_card = page.locator(".asset-card").first
    expect(first_card).to_be_visible()
    expect(first_card.locator("[data-open-detail]")).to_have_count(0)
    expect(first_card.locator("[data-compare-item]")).to_have_count(0)
    first_card.click()

    modal = page.locator("#detail-dialog")
    expect(modal).to_be_visible()
    expect(page.locator("#modal-title")).not_to_be_empty()
    original_title = page.locator("#modal-title").inner_text()
    expect(modal.locator(".ux-provenance-section")).to_have_count(0)
    evidence = modal.locator(".compatibility-evidence")
    expect(evidence).to_be_visible()
    expect(evidence).to_contain_text("購入前の互換性確認")
    expect(evidence).to_contain_text("最終判断")
    expect(page.locator("#modal-booth-link")).to_contain_text("BOOTHで最新情報を確認")
    expect(page).to_have_url(re.compile(r"#item-[^#]+$"))

    shared_url = page.url
    page.reload()
    wait_for_catalogue(page)
    expect(modal).to_be_visible(timeout=10000)
    expect(page.locator("#modal-title")).to_have_text(original_title)
    assert page.url == shared_url

    page.locator("#modal-close-btn").click()
    expect(modal).to_be_hidden()
    assert "#item-" not in page.url


def test_search_functionality_and_url_restore(page: Page):
    page.goto("http://localhost:8080/")
    wait_for_catalogue(page)

    search_bar = page.locator("#search-bar")
    search_bar.fill("桔梗")
    page.wait_for_timeout(500)

    expect(page.locator(".ux-results-summary")).to_contain_text("条件で絞り込み")
    expect(page.locator(".asset-card").first).to_be_visible()
    expect(page).to_have_url(re.compile(r"[?&]q=%E6%A1%94%E6%A2%97"))

    restored_url = page.url
    page.reload()
    wait_for_catalogue(page)
    expect(page.locator("#search-bar")).to_have_value("桔梗")
    assert page.url == restored_url


def test_removed_comparison_and_evidence_controls_are_absent(page: Page):
    page.goto("http://localhost:8080/")
    wait_for_catalogue(page)

    expect(page.locator("[data-compare-item]")).to_have_count(0)
    expect(page.locator("[data-open-detail]")).to_have_count(0)
    expect(page.locator("#ux-compare-tray")).to_have_count(0)
    expect(page.locator("#ux-comparison-panel")).to_have_count(0)
    expect(page.locator(".asset-provenance")).to_have_count(0)
    expect(page.locator(".ux-provenance-section")).to_have_count(0)
    expect(page.locator(".why-shown")).to_have_count(0)
    expect(page.get_by_text("この商品が表示された理由", exact=True)).to_have_count(0)
    assert "compare=" not in page.url


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


def test_compatibility_evidence_fits_narrow_mobile(page: Page):
    page.set_viewport_size({"width": 320, "height": 700})
    page.goto("http://localhost:8080/")
    wait_for_catalogue(page)
    page.locator(".asset-card").first.click()
    evidence = page.locator("#detail-dialog .compatibility-evidence")
    expect(evidence).to_be_visible()
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


def test_seller_market_report_accepts_real_catalog_item_url_and_restores(page: Page):
    payload = json.loads(Path("dist/api/seller_market_report.json").read_text(encoding="utf-8"))
    seller = next(row for row in payload["sellers"] if row.get("item_ids"))
    item_id = seller["item_ids"][0]

    response = page.goto("http://localhost:8080/seller/market-report/")
    assert response.status == 200
    expect(page.locator("#status")).to_contain_text("販売者", timeout=10000)

    page.locator("#seller-input").fill(f"https://booth.pm/ja/items/{item_id}")
    page.locator("#show-report").click()

    expect(page.locator("#report")).to_be_visible()
    expect(page.locator("#seller-name")).to_have_text(f"{seller['seller_name']} の市場スナップショット")
    expect(page.locator("#item-count")).to_have_text(f"{seller['item_count']:,}")
    expect(page).to_have_url(re.compile(r"[?&]seller="))
    expect(page.locator("#business-inquiry")).to_have_attribute("href", re.compile(r"title="))
    expect(page.locator("#new-product-inquiry")).to_have_attribute("href", re.compile(r"title="))
    expect(page.locator("#monthly-report-inquiry")).to_have_attribute("href", re.compile(r"title="))

    restored_url = page.url
    page.reload()
    expect(page.locator("#report")).to_be_visible(timeout=10000)
    expect(page.locator("#seller-name")).to_have_text(f"{seller['seller_name']} の市場スナップショット")
    assert page.url == restored_url
