#!/usr/bin/env python3
"""Debug script to analyze what ad networks are actually on Daily Mail."""
import json
import logging
from playwright.sync_api import sync_playwright
import random

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]

def debug_daily_mail():
    """Analyze Daily Mail for ads and ad networks."""
    print("\n" + "="*60)
    print("DAILY MAIL AD NETWORK DEBUG")
    print("="*60 + "\n")

    captured_requests = []

    def capture_request(route):
        """Capture all network requests."""
        request = route.request
        url = request.url

        # Log all ad-related requests
        if any(x in url for x in ['taboola', 'outbrain', 'mgid', 'revcontent', 'ads', 'sponsored']):
            captured_requests.append({
                'url': url,
                'method': request.method,
            })
            print(f"[NETWORK] {request.method} {url[:100]}")

        route.continue_()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            viewport={"width": 1440, "height": 900},
            locale="en-US",
            timezone_id="America/New_York",
        )
        page = context.new_page()

        # Capture all requests
        page.route("**/*", capture_request)

        url = "https://www.dailymail.co.uk/health/index.html"
        print(f"[INFO] Opening: {url}")

        try:
            page.goto(url, wait_until="networkidle", timeout=30_000)
            print("[INFO] Initial load complete, waiting for async JS...")
            page.wait_for_timeout(8000)
            print("[INFO] Waiting for additional network activity...")
            page.wait_for_timeout(5000)

            # Get page content and analyze
            print("\n[ANALYSIS] Checking DOM for ad containers...")

            # Check for various ad selectors
            selectors_to_check = [
                ("[id^='taboola-']", "Taboola containers"),
                (".trc-content-sponsored", "Taboola sponsored"),
                ("[data-outbrain]", "Outbrain"),
                ("[id*='MGID']", "MGID"),
                ("[id*='revcontent']", "RevContent"),
                ("[class*='sponsored']", "Sponsored class"),
                ("iframe[src*='taboola']", "Taboola iframe"),
                ("iframe[src*='outbrain']", "Outbrain iframe"),
                ("iframe[src*='mgid']", "MGID iframe"),
                (".sponsored-content", "Sponsored content div"),
                ("[data-ad-unit]", "Ad units"),
            ]

            for selector, name in selectors_to_check:
                try:
                    count = len(page.query_selector_all(selector))
                    if count > 0:
                        print(f"  ✓ {name}: {count} found (selector: {selector})")
                except:
                    pass

            # Check for specific headline/article selectors
            print("\n[ANALYSIS] Looking for content/headlines...")

            content_selectors = [
                ("article", "Article elements"),
                (".article", "Article class"),
                ("[class*='story']", "Story elements"),
                ("h2", "H2 headlines"),
                ("h3", "H3 headlines"),
                (".trc-item-title", "Taboola titles"),
            ]

            for selector, name in content_selectors:
                try:
                    count = len(page.query_selector_all(selector))
                    if count > 0:
                        print(f"  ✓ {name}: {count} found (selector: {selector})")
                        # Get first 3 examples
                        elements = page.query_selector_all(selector)[:3]
                        for i, el in enumerate(elements):
                            try:
                                text = el.inner_text()[:60]
                                print(f"    - Example {i+1}: {text}")
                            except:
                                pass
                except:
                    pass

            # Get all iframes
            print("\n[ANALYSIS] Checking iframes...")
            iframes = page.query_selector_all("iframe")
            print(f"  Total iframes: {len(iframes)}")
            for i, iframe in enumerate(iframes):
                try:
                    src = iframe.get_attribute("src") or ""
                    id_attr = iframe.get_attribute("id") or ""
                    data_attrs = iframe.get_attribute("data-src") or ""
                    print(f"    - Iframe {i+1}: id={id_attr}, src={src[:80] if src else 'none'}")
                except:
                    pass

            # Check for common content containers
            print("\n[ANALYSIS] Checking page structure...")
            page_content = page.content()

            if 'taboola' in page_content.lower():
                print("  ✓ 'taboola' found in page HTML")
            if 'outbrain' in page_content.lower():
                print("  ✓ 'outbrain' found in page HTML")
            if 'mgid' in page_content.lower():
                print("  ✓ 'mgid' found in page HTML")
            if 'revcontent' in page_content.lower():
                print("  ✓ 'revcontent' found in page HTML")

            # Look for story/article divs with links
            print("\n[ANALYSIS] Looking for clickable content...")
            links = page.query_selector_all("a[href*='health']")
            print(f"  Health-related links: {len(links)}")
            for link in links[:5]:
                try:
                    href = link.get_attribute("href")
                    text = link.inner_text()[:50]
                    if text:
                        print(f"    - {text} → {href[:60]}")
                except:
                    pass

            # Summary
            print(f"\n[SUMMARY] Captured {len(captured_requests)} ad-related requests")
            for req in captured_requests[:10]:
                print(f"  - {req['method']} {req['url'][:100]}")

        except Exception as e:
            print(f"[ERROR] {e}")
        finally:
            browser.close()

    print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    debug_daily_mail()
