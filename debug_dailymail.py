from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()

    url = "https://www.dailymail.co.uk/health/index.html"
    print(f"Loading {url}...")

    try:
        page.goto(url, wait_until="networkidle", timeout=30000)
    except Exception as e:
        print(f"Timeout or error: {e}")
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=15000)
        except:
            pass

    print("Page loaded, waiting...")
    time.sleep(3)

    html = page.content()
    print(f"\nHTML length: {len(html)}")

    # Look for native ad containers
    print("\nSearching for native ad elements...")

    patterns = [
        ("Taboola containers", "taboola"),
        ("Outbrain containers", "outbrain"),
        ("Sponsored content", "sponsored"),
        ("Native ad wrappers", "native"),
        ("Advertisement divs", "advertisement"),
    ]

    for name, pattern in patterns:
        count = html.lower().count(pattern)
        if count > 0:
            print(f"  {name}: {count} occurrences")

    # Look for actual section structure
    print("\nLooking at page structure...")

    # Save first 20000 chars for inspection
    with open("dailymail_sample.html", "w", encoding="utf-8") as f:
        f.write(html[:20000])

    print("Saved first 20KB to dailymail_sample.html")

    # Try to extract all headline-like elements
    headlines = page.query_selector_all("h1, h2, h3, [class*='headline'], [class*='title']")
    print(f"\nFound {len(headlines)} headline elements")
    if headlines:
        for i, h in enumerate(headlines[:5]):
            text = h.inner_text().strip()[:80]
            print(f"  {i+1}. {text}")

    # Look for links that might be ads
    all_links = page.query_selector_all("a")
    print(f"\nTotal links on page: {len(all_links)}")

    browser.close()
