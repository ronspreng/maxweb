# How to re-derive the API if it breaks

The endpoint, field names, and auth could all change tomorrow. Here's the 3-minute procedure to verify or rediscover them.

## Procedure

1. Log into `https://affiliates-backoffice.maxweb.com` in Chrome.
2. Open DevTools (F12), go to **Network** tab, set filter to **Fetch/XHR**, check "Preserve log".
3. Click the page you want to inspect (e.g., **Campaigns** in the sidebar).
4. Look for requests to `affiliates-backoffice-api.maxweb.com` — the SPA's API host. Each menu item corresponds to one or two of these.
5. Click the request → **Headers** tab confirms method, URL, and required headers (cookies, auth headers, etc.). **Response** tab shows the JSON shape.

If the API host has changed, you'll spot it immediately — the new requests will go to a different domain.

## Faster: query the SPA's XHR wrapper directly

The SPA exposes its XHR wrapper on `window.SPIDashboard.xhr`. From the DevTools console you can list and call any endpoint by name without leaving the browser:

```js
// What endpoints does the SPA know about?
// (these are the names passed to SPIDashboard.xhr.get/post)
// Find them by searching the JS bundle for "SPIDashboard.xhr.get(" — DevTools Sources tab → Cmd/Ctrl+F → that string.

// Try one:
const r = await SPIDashboard.xhr.get('get-popular-products');
console.log(r.result, r.data?.length, Object.keys(r.data?.[0] || {}));
```

The wrapper resolves the endpoint name to a URL — sniff it by overriding XHR before calling:

```js
const orig = XMLHttpRequest.prototype.open;
XMLHttpRequest.prototype.open = function(m, u) { console.log('XHR', m, u); return orig.apply(this, arguments); };
const r = await SPIDashboard.xhr.get('get-popular-products');
```

That logs the exact URL the wrapper hits. If MaxWeb migrates to a new host, this is how you find out.

## Spotting auth changes

If the script gets a 401/403 and the cookie is fresh, the API likely added a CSRF token or auth header. Check the request headers in DevTools — anything beyond `Cookie: sessid3=...` and `Accept: */*` is new and needs to be replicated in the scraper.

Common additions to look for:
- `X-Csrf-Token: ...` — usually fetchable from a meta tag or a separate `/csrf` endpoint
- `Authorization: Bearer ...` — would mean they migrated to OAuth, in which case auth flow needs full redesign
- A custom header like `X-MW-Client: ...` — usually a static string the SPA hardcodes; copy it verbatim

## Verifying the response shape

The scraper assumes `{ result: 1, data: [...] }`. If the envelope changes, update `fetch()` in `maxweb_scraper.py`. To check quickly:

```python
import requests, json
r = requests.get(
    "https://affiliates-backoffice-api.maxweb.com/get-popular-products",
    cookies={"sessid3": "..."},
    headers={"Accept": "*/*", "Origin": "https://affiliates-backoffice.maxweb.com"},
)
print(r.status_code)
print(json.dumps(r.json(), indent=2)[:2000])
```

## When all else fails

The MaxWeb support team / your dedicated AM is the canonical source. They may have an official postback or S2S feed (third-party tools like wecantrack reportedly have an integration), even if it's not publicly documented. Asking is always cheaper than reverse-engineering for the second time.
