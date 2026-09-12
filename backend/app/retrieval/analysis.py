"""Market analysis module for Agent 2 Property Search.

Computes descriptive statistics and signals over the filtered result set
so that downstream agents (Agent 4) and the frontend have market context
without raw data.

For ``LAND_AND_HOUSE`` intent, Agent 2 deliberately does NOT compute a
land/construction budget split.  That responsibility belongs to Agent 3
which receives ``total_project_budget_lkr`` from Agent 2's metadata.
"""

from __future__ import annotations

import pandas as pd

from app.schemas.requirements import Intent, ParsedRequirements


def _price_column(requirements: ParsedRequirements) -> str:
    listing_type = (requirements.listing_type or "").lower()
    return "rent_monthly_lkr" if listing_type == "rent" else "sale_total_price_lkr"


def compute_analysis(
    df_filtered: pd.DataFrame,
    requirements: ParsedRequirements,
) -> dict:
    """Return a market-analysis dict over the already-filtered DataFrame.

    Keys
    ----
    price_stats        Price statistics (min/max/median/mean/count).
    budget_fit_pct     Percentage of filtered results within max budget.
    district_breakdown Property count per district.
    verified_count     Number of verified listings in the filtered set.
    property_type_breakdown  Count per property_type.
    land_and_house     Present only for LAND_AND_HOUSE intent; contains
                       total_project_budget_lkr for Agent 3 to consume.
    """
    analysis: dict = {}

    if df_filtered.empty:
        analysis["price_stats"] = {
            "min_price": None,
            "max_price": None,
            "median_price": None,
            "mean_price": None,
            "count": 0,
        }
        analysis["budget_fit_pct"] = 0.0
        analysis["district_breakdown"] = {}
        analysis["verified_count"] = 0
        analysis["property_type_breakdown"] = {}
        return analysis

    price_col = _price_column(requirements)
    prices = df_filtered[price_col].dropna()

    # ── Price statistics ──────────────────────────────────────────────────────
    analysis["price_stats"] = {
        "min_price": round(float(prices.min()), 2) if not prices.empty else None,
        "max_price": round(float(prices.max()), 2) if not prices.empty else None,
        "median_price": round(float(prices.median()), 2) if not prices.empty else None,
        "mean_price": round(float(prices.mean()), 2) if not prices.empty else None,
        "count": int(prices.count()),
    }

    # ── Budget fit ─────────────────────────────────────────────────────────────
    max_budget = requirements.maximum_budget_lkr
    if max_budget and not prices.empty:
        within_budget = int((prices <= max_budget).sum())
        analysis["budget_fit_pct"] = round(within_budget / len(prices) * 100, 1)
    else:
        analysis["budget_fit_pct"] = 100.0

    # ── District breakdown ────────────────────────────────────────────────────
    if "district" in df_filtered.columns:
        district_counts = (
            df_filtered["district"]
            .fillna("Unknown")
            .value_counts()
            .to_dict()
        )
        analysis["district_breakdown"] = {str(k): int(v) for k, v in district_counts.items()}
    else:
        analysis["district_breakdown"] = {}

    # ── Verified count ─────────────────────────────────────────────────────────
    analysis["verified_count"] = int(df_filtered["is_verified"].sum()) if "is_verified" in df_filtered.columns else 0

    # ── Property type breakdown ───────────────────────────────────────────────
    if "property_type" in df_filtered.columns:
        type_counts = df_filtered["property_type"].fillna("Unknown").value_counts().to_dict()
        analysis["property_type_breakdown"] = {str(k): int(v) for k, v in type_counts.items()}
    else:
        analysis["property_type_breakdown"] = {}

    # ── LAND_AND_HOUSE: pass budget info to Agent 3 ───────────────────────────
    if requirements.intent == Intent.LAND_AND_HOUSE:
        analysis["land_and_house"] = {
            "total_project_budget_lkr": requirements.total_project_budget_lkr,
            "note": "Budget split between land and construction is handled by Agent 3.",
        }

    return analysis
