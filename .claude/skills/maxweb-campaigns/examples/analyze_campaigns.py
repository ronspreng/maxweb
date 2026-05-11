"""Richer analysis template for MaxWeb campaign data.

Functions you can crib for ad-hoc queries:
- summarize_by_category()
- top_n(metric, n)
- filter_offers(...)

Assumes campaigns.csv exists in ./data — run the scraper first.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

DEFAULT_CSV = Path("data/campaigns.csv")


def load(path: Path = DEFAULT_CSV) -> pd.DataFrame:
    df = pd.read_csv(path)
    # Ensure numeric columns really are numeric (read_csv usually gets it right,
    # but if anyone edited the CSV we want a clean coerce)
    for col in [
        "avg_ltv",
        "avg_payout",
        "epc_alltime",
        "conversion_rate_alltime",
        "refundrate_alltime",
        "visitors_alltime",
        "trending",
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df["is_promotable"] = df["flag_approved"].astype(str) != "0"
    return df


def summarize_by_category(df: pd.DataFrame) -> pd.DataFrame:
    """Mean payout / EPC / CR + offer count per category, promotable only."""
    sub = df[df["is_promotable"]]
    g = sub.groupby("category", dropna=False).agg(
        offer_count=("name", "count"),
        avg_payout_mean=("avg_payout", "mean"),
        epc_mean=("epc_alltime", "mean"),
        cr_mean=("conversion_rate_alltime", "mean"),
        traffic_total=("visitors_alltime", "sum"),
    )
    return g.sort_values("epc_mean", ascending=False).round(2)


def top_n(df: pd.DataFrame, metric: str = "epc_alltime", n: int = 20) -> pd.DataFrame:
    cols = [
        "name",
        "category",
        "avg_payout",
        "epc_alltime",
        "conversion_rate_alltime",
        "visitors_alltime",
    ]
    return (
        df[df["is_promotable"]]
        .sort_values(metric, ascending=False)
        .head(n)[cols]
        .reset_index(drop=True)
    )


def filter_offers(
    df: pd.DataFrame,
    min_payout: float = 0,
    min_epc: float = 0,
    category_contains: str | None = None,
    min_traffic: float = 0,
) -> pd.DataFrame:
    """Lightweight filter. Each kwarg is optional."""
    mask = (
        df["is_promotable"]
        & (df["avg_payout"] >= min_payout)
        & (df["epc_alltime"] >= min_epc)
        & (df["visitors_alltime"] >= min_traffic)
    )
    if category_contains:
        mask &= df["category"].str.contains(category_contains, case=False, na=False)
    return df[mask]


if __name__ == "__main__":
    df = load()
    print(f"Loaded {len(df)} campaigns ({df['is_promotable'].sum()} promotable)\n")

    print("=== Top 10 by EPC (promotable only) ===")
    print(top_n(df, "epc_alltime", 10).to_string(index=False))

    print("\n=== Categories ranked by mean EPC ===")
    print(summarize_by_category(df).head(10).to_string())

    print("\n=== Beauty offers with payout >= $50 ===")
    sample = filter_offers(df, min_payout=50, category_contains="beauty")
    print(sample[["name", "avg_payout", "epc_alltime"]].to_string(index=False))
