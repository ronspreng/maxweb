"""Print the top 20 MaxWeb campaigns by Earnings Per Click.

Assumes you've already run the scraper, e.g.:
    python .claude/skills/maxweb-campaigns/scripts/maxweb_scraper.py --out ./data
"""

import pandas as pd

df = pd.read_csv("data/campaigns.csv")

# Only campaigns we can actually promote
promotable = df[df["flag_approved"].astype(str) != "0"]

cols = [
    "name",
    "category",
    "avg_payout",
    "epc_alltime",
    "conversion_rate_alltime",
    "visitors_alltime",
]
top = promotable.sort_values("epc_alltime", ascending=False).head(20)[cols]
print(top.to_string(index=False))
