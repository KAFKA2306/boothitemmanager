import json
import subprocess
import sys
import time
from typing import Generator, Dict, Any
import pytest
import requests
from playwright.sync_api import Page, expect

@pytest.fixture(scope="session", autouse=True)
def start_seo_server() -> Generator[str, None, None]:
    # Start a thread-safe multi-threaded HTTP server inline to prevent blocking connections
    server_code = """
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
class SilentHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass
server = ThreadingHTTPServer(('', 8081), lambda *a, **k: SilentHandler(*a, directory='dist', **k))
server.serve_forever()
"""
    process = subprocess.Popen([sys.executable, "-c", server_code])
    
    # Poll until the server is ready to accept requests
    for _ in range(20):
        try:
            r = requests.get("http://localhost:8081/")
            if r.status_code == 200:
                break
        except requests.ConnectionError:
            pass
        time.sleep(0.2)
    else:
        process.terminate()
        raise RuntimeError("Could not start local test server on port 8081")
        
    yield "http://localhost:8081"
    process.terminate()

def test_seo_metadata(page: Page) -> None:
    js_errors: list[str] = []
    page.on("pageerror", lambda err: js_errors.append(err.message))

    page.goto("http://localhost:8081/")
    expect(page.locator("#splash")).to_be_hidden(timeout=10000)
    
    # Verify no script or runtime errors on load
    assert not js_errors, f"JavaScript errors occurred: {js_errors}"

    # Basic Document SEO settings
    assert page.locator("html").get_attribute("lang") == "ja"
    assert page.locator("meta[charset]").get_attribute("charset") == "UTF-8"
    assert page.title() == "BoothItemManager2 - VRChat Booth Asset Discovery"

    # Core SEO meta tags
    expect(page.locator('meta[name="description"]')).to_have_attribute(
        "content", 
        "Discover VRChat assets from Booth. Filter by avatar compatibility, style, color, category, and price instantly."
    )
    expect(page.locator('meta[name="keywords"]')).to_have_attribute(
        "content",
        "VRChat, Booth, 3D Assets, Avatar, Outfit, Accessory, Gimmick, Discovery, Search, Compatibility, PhysBone, Modular Avatar"
    )
    expect(page.locator('meta[name="robots"]')).to_have_attribute(
        "content",
        "index, follow, max-snippet:-1, max-image-preview:large, max-video-preview:-1"
    )
    expect(page.locator('link[rel="canonical"]')).to_have_attribute(
        "href",
        "https://boothitemmanager.pages.dev/"
    )

    # OpenGraph (OGP)
    expect(page.locator('meta[property="og:title"]')).to_have_attribute(
        "content", "BoothItemManager2 - VRChat Booth Asset Discovery"
    )
    expect(page.locator('meta[property="og:description"]')).to_have_attribute(
        "content",
        "Discover VRChat virtual assets, outfits, accessories, hairstyles, and gimmicks from Booth.pm. Filter instantly by base avatar compatibility, style, color, category, and price."
    )
    expect(page.locator('meta[property="og:type"]')).to_have_attribute("content", "website")
    expect(page.locator('meta[property="og:url"]')).to_have_attribute(
        "content", "https://boothitemmanager.pages.dev/"
    )
    expect(page.locator('meta[property="og:image"]')).to_have_attribute(
        "content", "https://placehold.jp/24/12121a/00f0ff/1200x630.png?text=BoothItemManager2"
    )
    expect(page.locator('meta[property="og:site_name"]')).to_have_attribute(
        "content", "BoothItemManager2"
    )
    expect(page.locator('meta[property="og:locale"]')).to_have_attribute(
        "content", "ja_JP"
    )

    # Twitter Cards
    expect(page.locator('meta[name="twitter:card"]')).to_have_attribute("content", "summary_large_image")
    expect(page.locator('meta[name="twitter:title"]')).to_have_attribute("content", "BoothItemManager2 - VRChat Booth Asset Discovery")
    expect(page.locator('meta[name="twitter:image"]')).to_have_attribute("content", "https://placehold.jp/24/12121a/00f0ff/1200x630.png?text=BoothItemManager2")

    # GEO / AI Citations
    expect(page.locator('meta[name="citation_title"]')).to_have_attribute("content", "BoothItemManager2 - VRChat Booth Asset Discovery")
    expect(page.locator('meta[name="citation_author"]')).to_have_attribute("content", "BoothItemManager Contributors")
    expect(page.locator('meta[name="ai-optimized"]')).to_have_attribute("content", "true")
    expect(page.locator('meta[name="search-engine"]')).to_have_attribute("content", "generative-engine-optimization")

def test_structured_data_ld_json(page: Page) -> None:
    page.goto("http://localhost:8081/")
    expect(page.locator("#splash")).to_be_hidden(timeout=10000)

    # Extract JSON-LD structured data script
    script_content: str = page.locator('script[type="application/ld+json"]').inner_html()
    data: Dict[str, Any] = json.loads(script_content)

    # Verify structured schemas
    assert data["@context"] == "https://schema.org"
    assert data["@type"] == "WebApplication"
    assert data["name"] == "BoothItemManager2"
    assert data["url"] == "https://boothitemmanager.pages.dev/"
    assert "offers" in data
    assert data["offers"]["@type"] == "Offer"
    assert data["offers"]["price"] == "0"
    assert data["offers"]["priceCurrency"] == "JPY"
    assert len(data["featureList"]) >= 5

def test_link_integrity_and_crawling(page: Page) -> None:
    page.goto("http://localhost:8081/")
    expect(page.locator("#splash")).to_be_hidden(timeout=10000)

    # Crawl initial links
    links = page.locator("a")
    link_count = int(links.count())
    assert link_count > 0

    for i in range(link_count):
        href = links.nth(i).get_attribute("href")
        assert href is not None
        # Must be either "/" or start with https:// or be empty javascript/modal links
        assert href == "/" or href.startswith("https://") or href == ""

    # Test logo link
    logo = page.locator("a.logo")
    expect(logo).to_have_attribute("href", "/")

    # Trigger detail modal to check dynamically loaded external links
    first_card = page.locator(".asset-card").first
    expect(first_card).to_be_visible()
    first_card.click()

    modal = page.locator("#detail-dialog")
    expect(modal).to_be_visible()

    # Check Booth redirect link
    booth_link = page.locator("#modal-booth-link")
    expect(booth_link).to_have_attribute("target", "_blank")
    href_booth = booth_link.get_attribute("href")
    assert href_booth is not None
    assert href_booth.startswith("https://booth.pm/")

    # Check SNS Shortcut Links
    x_link = page.locator("a.social-x")
    expect(x_link).to_have_attribute("target", "_blank")
    href_x = x_link.get_attribute("href")
    assert href_x is not None
    assert "x.com" in href_x

    insta_link = page.locator("a.social-insta")
    expect(insta_link).to_have_attribute("target", "_blank")
    href_insta = insta_link.get_attribute("href")
    assert href_insta is not None
    assert "instagram.com" in href_insta

    tiktok_link = page.locator("a.social-tiktok")
    expect(tiktok_link).to_have_attribute("target", "_blank")
    href_tiktok = tiktok_link.get_attribute("href")
    assert href_tiktok is not None
    assert "tiktok.com" in href_tiktok

    # Close modal
    page.locator("#modal-close-btn").click()
    expect(modal).to_be_hidden()

def test_layout_and_responsive_audit(page: Page) -> None:
    page.goto("http://localhost:8081/")
    expect(page.locator("#splash")).to_be_hidden(timeout=10000)

    # 1. Desktop Viewport Layout Validation
    page.set_viewport_size({"width": 1280, "height": 800})
    page.wait_for_timeout(200) # yield control to allow viewport recalculations

    header = page.locator("header")
    aside = page.locator("aside")
    main = page.locator("main")

    expect(header).to_be_visible()
    expect(aside).to_be_visible()
    expect(main).to_be_visible()

    h_box = header.bounding_box()
    a_box = aside.bounding_box()
    m_box = main.bounding_box()

    assert h_box is not None
    assert a_box is not None
    assert m_box is not None

    # Header resides at y=0, with height > 0
    assert h_box["y"] == 0
    assert h_box["height"] > 0

    # Sidebar is positioned below header, flush left
    assert a_box["y"] >= h_box["height"]
    assert a_box["x"] == 0
    assert a_box["width"] > 0

    # Main content is to the right of the sidebar
    assert m_box["y"] >= h_box["height"]
    assert m_box["x"] >= a_box["width"]

    # 2. Mobile Viewport Layout Validation
    page.set_viewport_size({"width": 375, "height": 667})
    page.wait_for_timeout(200)

    # Sidebar (aside) must be hidden on mobile screen widths
    expect(aside).to_be_hidden()
    expect(header).to_be_visible()
    expect(main).to_be_visible()

    mh_box = header.bounding_box()
    mm_box = main.bounding_box()

    assert mh_box is not None
    assert mm_box is not None

    # Header at y=0, main content stacks vertically beneath it
    assert mh_box["y"] == 0
    assert mm_box["y"] >= mh_box["y"] + mh_box["height"]

def test_image_accessibility(page: Page) -> None:
    page.goto("http://localhost:8081/")
    expect(page.locator("#splash")).to_be_hidden(timeout=10000)

    # Assert that all visible images have alt attributes defined
    images = page.locator("img")
    img_count = int(images.count())
    assert img_count > 0

    for i in range(img_count):
        img = images.nth(i)
        if img.is_visible():
            alt = img.get_attribute("alt")
            assert alt is not None, "Image missing alt attribute"
            assert len(alt.strip()) > 0, "Alt attribute must not be empty"
