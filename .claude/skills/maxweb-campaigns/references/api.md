# MaxWeb internal API — endpoint inventory

> Reverse-engineered from `https://affiliates-backoffice.maxweb.com/app` SPA source on 2026-05-08. Unofficial. Subject to change without notice.

## Authentication

- **Cookie:** `sessid3`, set on `.maxweb.com` after login + 2FA.
- **No API key, no bearer token, no CSRF header.** XHRs in the SPA are sent with `withCredentials: true` and only `Accept: */*` as a custom header.
- **Origin/Referer:** browser sets `https://affiliates-backoffice.maxweb.com` — the API tolerates either presence or absence of these headers when called from a non-browser client, but include them defensively.

## Base URL

```
https://affiliates-backoffice-api.maxweb.com
```

Note the suffix `-api` — the SPA itself is on `affiliates-backoffice.maxweb.com` (no `-api`).

## Response shape

All JSON endpoints follow the same envelope:

```json
{
  "result": 1,
  "result_str": "",
  "data": <payload>
}
```

`result == 1` means success. Anything else (typically `0`) means failure and `result_str` contains the message. The scraper raises `RuntimeError` on `result != 1`.

## Confirmed endpoints

### GET /get-popular-products

The Campaigns table. Returns ~500 records, no pagination, no filters.

- **Method:** GET
- **Params:** none observed
- **Response:** `data: [ {...campaign...}, ... ]`
- **Field reference:** see `data_dictionary.md`

### GET /get-categories

The categorie-list used in the Campaigns category filter.

- **Response:** `data: [ { id, name }, ... ]` (43 entries)
- Useful to resolve `category_id_maxweb` → human name when joining with offer records.

## Other endpoints observed in SPA source (not implemented in scraper)

These are all called via `SPIDashboard.xhr.get('<name>')` or `.post(...)` in the JavaScript bundle. Same auth, same envelope — only the path changes.

| Endpoint | Method | Purpose |
|---|---|---|
| `get-affiliate-info` | GET | Account profile + settings |
| `get-account-summary` | GET | Aggregate stats for the dashboard tiles |
| `get-active-promotions` | GET | Currently approved offers for this affiliate |
| `get-promoted-offers` | GET | Offers this affiliate has been approved on |
| `get-pending-payments` | GET | Pending payouts |
| `get-completed-payments` | GET | Payout history |
| `get-postback-pixels` | GET | Server-to-server postback config |
| `get-external-pixels` | GET | Pixel/event configuration |
| `get-affiliate-links` | GET | Tracking URLs per offer (optionally filtered by offer id) |
| `promote-offer` | GET | Apply to promote an offer. Param: `offer_account_id` |
| `get-popular-products` | GET | (already implemented) Campaigns table |
| `get-categories` | GET | (already implemented) Category list |

## Adding a new endpoint to the scraper

The scraper's `fetch()` is endpoint-agnostic. To add e.g. promoted offers:

```python
promoted = fetch(session, "get-promoted-offers")
```

Then write your own normalizer or just dump the raw list. If the response shape ever differs from the standard envelope (which doesn't seem to happen in this API as of 2026-05-08), guard against it.

## When the contract breaks

If the script suddenly returns 401/403/redirects:

1. Re-login in the browser, grab a fresh `sessid3`. 95% of breakages are an expired cookie.
2. If still failing: see `reverse_engineering.md` — there's a 3-minute DevTools procedure to verify the endpoint URL, parameters, and required headers haven't changed.
