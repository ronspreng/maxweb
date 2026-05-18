import requests

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}

url = "https://www.dailymail.co.uk/health/index.html"
print(f"Testing {url} with requests...")

try:
    resp = requests.get(url, headers=headers, timeout=10)
    print(f"Status: {resp.status_code}")
    print(f"Content-Type: {resp.headers.get('content-type')}")
    print(f"Content length: {len(resp.text)}")

    if resp.status_code == 200:
        # Check for key content
        if "Access Denied" in resp.text:
            print("Response: Access Denied page")
        elif "taboola" in resp.text.lower():
            print("Found Taboola in response")
        elif "outbrain" in resp.text.lower():
            print("Found Outbrain in response")
        else:
            print(f"First 500 chars: {resp.text[:500]}")
    else:
        print(f"Error response: {resp.text[:200]}")

except Exception as e:
    print(f"Error: {e}")
