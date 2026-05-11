# `get-popular-products` — field reference

Each record in the response array has the following fields. Types reflect what the wire returns; the scraper post-processes numerics into floats.

| Field | Wire type | Meaning | Notes |
|---|---|---|---|
| `account_id` | str (digits) | MaxWeb internal offer ID | Unique per offer. Same as `_account_id`. |
| `_account_id` | str (digits) | Duplicate of `account_id` | Legacy SPA usage. Ignore. |
| `name` | str | Product display name | E.g., "Trimology", "AlphaFuel Pro V2" |
| `cartproductname` | str | Cart-page display name | Often matches `name` but can differ for localized variants |
| `codename` | str | Slug | snake_case version of name |
| `rr_record_id` | str (digits) | Internal versioning ID | Rarely useful |
| `description` | HTML str | Marketing description | Contains `<p>` tags. Strip for plain text. |
| `product_image` | URL | Thumbnail | 160px CDN URL |
| `category_id_maxweb` | str (digits) | Category ID | Join with `/get-categories` |
| `category` | str | Category name | Sometimes empty in raw data — scraper backfills |
| `commissionplanname` | str | Human-readable commission structure | E.g., "0% Frontend, 0% Backend" |
| `commissionplantype` | str | Commission type code | E.g., "backend", "frontend" |
| `avg_ltv` | str (zero-padded) | Average product price | Cast to float. **Note:** for `category_id_maxweb` 422 or 386 the SPA forces this to 0 — odd legacy logic; check your category. |
| `avg_payout` | str (zero-padded) | Average commission paid out per conversion | Cast to float. Currency depends on offer (USD by default; EUR for `_account_id` in `[6269, 6389, 6419, 6420, 6421, 6547, 7188, 7332, 7370, 7371, 7498]`; GBP for offer 7333 + cartproductname "ViaKeto Apple Gummies UK", else EUR for 7333) |
| `epc_alltime` | str | Earnings Per Click, alltime | Cast to float. The MaxWeb default sort field. |
| `conversion_rate_alltime` | str | Conversion rate %, alltime | Cast to float (already a percentage, e.g., 3.40 means 3.40%) |
| `refundrate_alltime` | str (zero-padded) | Refund rate %, alltime | Cast to float |
| `visitors_alltime` | str (zero-padded) | Total visitors, alltime | Cast to float (then int). The SPA buckets this for display ("New Offer", "5,000", "10,000+"). Raw is the actual number. |
| `trending` | str (zero-padded) | Internal trending score | Cast to float. SPA clamps display to >=5 but raw can be lower. |
| `negative_score` | str | Sentiment-style score (negative) | Always 0 in observed data so far |
| `positive_score` | str | Sentiment-style score (positive) | Always 0 in observed data so far |
| `flag_approved` | str | Approval state for this affiliate | `"0"` = not approved, `"1"` = approved (rare), `"2"` = active |
| `auto_approve` | str | Auto-approve enabled | If 1, "Promote" button creates the link instantly without manual review |
| `company_website` | URL | Tracking/lander URL | This is the affiliate's tracking link — contains affiliate-specific IDs in query params |
| `manage_link` | URL | Deep-link to manage panel | Used by SPA for "Manage Account" CTA (only for active offers) |
| `resources_link` | URL | Deep-link to creative assets | Empty if you're not yet promoting |
| `restrictions_link` | URL | Deep-link to offer restrictions page | E.g., banned traffic sources |

## Worked example

Raw record from the API:

```json
{
  "account_id": "12530",
  "name": "DentaBiome",
  "category_id_maxweb": "406",
  "avg_ltv": "000000000079.00",
  "avg_payout": "000000000160.00",
  "epc_alltime": "1",
  "conversion_rate_alltime": "1",
  "refundrate_alltime": "000000000000.00",
  "visitors_alltime": "000000003438.00",
  "trending": "000000000006.88",
  "flag_approved": "2"
}
```

After `normalize_record`:

```python
{
  "account_id": "12530",
  "name": "DentaBiome",
  "category": "Dental/Gum Health",  # backfilled
  "category_id_maxweb": "406",
  "avg_ltv": 79.0,
  "avg_payout": 160.0,
  "epc_alltime": 1.0,
  "conversion_rate_alltime": 1.0,
  "refundrate_alltime": 0.0,
  "visitors_alltime": 3438.0,
  "trending": 6.88,
  "flag_approved": "2",
  ...
}
```

## Computed fields you might want

These aren't in the API but are easy to derive:

- `revenue_per_visitor = avg_payout * (conversion_rate_alltime / 100)` — rough comparison metric across offers, equivalent to EPC but recomputable from price/payout.
- `est_lifetime_value = avg_ltv * conversion_rate_alltime / 100` — estimated revenue per visitor before costs.
- `is_promotable = flag_approved != "0"` — boolean, useful filter.
- `currency = ...` — see avg_payout currency rules above to derive.
