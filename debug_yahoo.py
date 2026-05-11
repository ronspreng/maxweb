#!/usr/bin/env python3
from playwright.sync_api import sync_playwright
import random

USER_AGENTS = ["Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"]

def debug_yahoo():
    print("\n=== YAHOO NEWS AD DEBUG ===\n")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=random.choice(USER_AGENTS), viewport={"width": 1440, "height": 900})
        page = context.new_page()

        url = "https://news.yahoo.com/lifestyle/health"
        print(f"[INFO] Opening: {url}\n")
        
        try:
            page.goto(url, wait_until="networkidle", timeout=30_000)
            page.wait_for_timeout(5000)

            # Check for native ads
            selectors = [
                ("[data-outbrain]", "Outbrain"),
                ("[class*='sponsored']", "Sponsored"),
                (".native-ad", "Native ad"),
                ("[id*='MGID']", "MGID"),
                ("article", "Articles"),
                ("a[href*='yahoo']", "Yahoo links"),
            ]

            for selector, name in selectors:
                count = len(page.query_selector_all(selector))
                if count > 0:
                    print(f"[FOUND] {name}: {count} elements")
                    if name == "Articles":
                        els = page.query_selector_all(selector)[:3]
                        for el in els:
                            text = el.inner_text()[:60] if el else ""
                            if text:
                                print(f"  - {text}")

            # Check page content
            content = page.content().lower()
            for keyword in ['outbrain', 'taboola', 'mgid', 'native-ad', 'sponsored']:
                if keyword in content:
                    print(f"[FOUND] '{keyword}' in page HTML")

        except Exception as e:
            print(f"[ERROR] {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    debug_yahoo()
