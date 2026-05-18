import requests
from urllib.parse import urlencode

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

# Try Amazon search
query = "brain health supplement"
url = f"https://www.amazon.com/s?{urlencode({'k': query})}"

print(f"Testing {url}...")

try:
    resp = requests.get(url, headers=headers, timeout=10)
    print(f"Status: {resp.status_code}")
    print(f"Content-Type: {resp.headers.get('content-type')}")
    print(f"Content length: {len(resp.text)}")

    if resp.status_code == 200:
        if "captcha" in resp.text.lower():
            print("Got CAPTCHA page")
        elif "sorry" in resp.text.lower():
            print("Got 'sorry' page (blocked)")
        else:
            # Count products
            product_count = resp.text.count("asin")
            print(f"Found ~{product_count} product references")
    else:
        print(f"Error: {resp.text[:200]}")

except Exception as e:
    print(f"Error: {e}")
