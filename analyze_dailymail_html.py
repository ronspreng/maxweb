import requests
from bs4 import BeautifulSoup
import json
import re

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

url = "https://www.dailymail.co.uk/health/index.html"
print(f"Fetching {url}...")

resp = requests.get(url, headers=headers, timeout=15)
print(f"Status: {resp.status_code}")

soup = BeautifulSoup(resp.text, "html.parser")

# Save HTML sample
with open("dailymail_full.html", "w", encoding="utf-8") as f:
    f.write(resp.text[:30000])

print(f"Saved HTML sample to dailymail_full.html")
print(f"\nAnalyzing page structure...")

# Count elements
taboola_divs = soup.find_all("div", id=re.compile(r"^taboola-"))
print(f"Found {len(taboola_divs)} Taboola divs")

# Look for script tags
script_tags = soup.find_all("script", type="application/json")
print(f"Found {len(script_tags)} JSON script tags")

# Look for taboola text anywhere
if "taboola" in resp.text.lower():
    # Find context
    idx = resp.text.lower().find("taboola")
    snippet = resp.text[max(0, idx-200):idx+500]
    print(f"\nFirst Taboola reference context:\n{snippet}\n")

# Look for window objects that might contain ads
window_objects = re.findall(r'window\.\w+\s*=\s*({.*?});', resp.text)
print(f"\nFound {len(window_objects)} window object assignments")

# Check for data attributes
data_attrs = soup.find_all(attrs={"data-taboola": True})
print(f"Found {len(data_attrs)} elements with data-taboola")

# List all divs with 'trc' or native ad related class
trc_divs = soup.find_all("div", class_=re.compile(r"(trc|native|ad|sponsored)"))
print(f"Found {len(trc_divs)} divs with ad-related classes")

# Check what we have in the actual body
body = soup.find("body")
if body:
    articles = body.find_all("article")
    print(f"\nFound {len(articles)} article tags")

    # Look for links
    links = body.find_all("a", href=True)
    print(f"Total links in body: {len(links)}")

    # Sample some links
    print("\nFirst 5 article-like links:")
    count = 0
    for link in links:
        text = link.get_text(strip=True)
        href = link.get("href")
        if len(text) > 20 and "health" in href.lower():
            print(f"  {text[:70]}... -> {href[:80]}")
            count += 1
            if count >= 5:
                break
