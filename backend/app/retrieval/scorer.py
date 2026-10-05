"""Soft scoring and ranking engine for Agent 2 Property Search.

Produces a continuous relevance score (0.0 – 1.0) for each listing by
combining weighted signals.  All computation is vectorised over the full
DataFrame so performance stays acceptable on 200 k+ rows.

Signal weights
--------------
budget_fit      0.35 – how far price sits below the ceiling (closer = better)
location_exact  0.20 – exact location match > district match > no match
bedroom_match   0.15 – exact bedroom count > within ±1 > anything
verified_bonus  0.12 – is_verified listing
size_fit        0.10 – property size vs stated minimum requirement
recency         0.08 – more recently posted listings rank higher
"""

from __future__ import annotations

import json
from datetime import datetime

import pandas as pd

from app.schemas.requirements import Intent, ParsedRequirements

# ── Weights ──────────────────────────────────────────────────────────────────
_W_LOCATION = 0.40
_W_BUDGET = 0.25
_W_BEDROOMS = 0.15
_W_SIZE = 0.10
_W_VERIFIED = 0.06
_W_RECENCY = 0.04

# Common location qualifiers to strip when matching
_LOCATION_QUALIFIERS = {
    "near", "around", "close to", "vicinity of", "vicinity",
    "city", "area", "zone", "region", "suburb",
    "district", "town", "town area",
}


def _normalize_location(location: str) -> list[str]:
    """Normalize a location phrase to extract searchable terms.
    
    Strips common qualifiers and returns both the original term and
    normalized versions for flexible matching.
    """
    if not location:
        return []
    
    normalized = location.strip().lower()
    result = [normalized]  # Always include the original
    
    # Try stripping each qualifier from start or end
    words = normalized.split()
    if len(words) > 1:
        # Strip leading qualifiers
        while words and words[0] in _LOCATION_QUALIFIERS:
            words.pop(0)
        # Strip trailing qualifiers  
        while words and words[-1] in _LOCATION_QUALIFIERS:
            words.pop()
        
        if words:
            core_term = " ".join(words)
            if core_term != normalized:
                result.append(core_term)
    
    return result


# ── Individual signal computers ───────────────────────────────────────────────

def _signal_budget(df: pd.DataFrame, requirements: ParsedRequirements) -> pd.Series:
    """Score based on how much headroom the price leaves below the budget ceiling."""
    listing_type = (requirements.listing_type or "").lower()
    budget = requirements.maximum_budget_lkr

    if budget is None or budget <= 0:
        return pd.Series(0.5, index=df.index)  # neutral when no budget given

    price_col = "rent_monthly_lkr" if listing_type == "rent" else "sale_total_price_lkr"
    prices = df[price_col].copy()

    # Replace NaN / 0 with budget so they get a neutral score
    prices = prices.where(prices.notna() & (prices > 0), other=float(budget))

    # Ratio of price to budget: 0.0 = free, 1.0 = exactly at ceiling
    ratio = (prices / budget).clip(upper=1.0)

    # Invert: 1.0 = cheapest relative to budget, 0.0 = at ceiling
    return (1.0 - ratio).clip(lower=0.0)


def _signal_location(df: pd.DataFrame, requirements: ParsedRequirements) -> pd.Series:
    """Score location match.
    
    Handles location phrases by stripping qualifiers (e.g., "near malabe" -> "malabe").
    - Exact location match = 1.0
    - District-only match = 0.5
    - No match = 0.0
    """
    location = (requirements.location or "").strip()
    district = (requirements.district or "").strip()

    signal = pd.Series(0.0, index=df.index)

    if location:
        # Normalize location to handle phrases like "near malabe", "malabe city"
        location_terms = _normalize_location(location)
        loc_col = df["location"].fillna("").str.lower()
        addr_col = df["address"].fillna("").str.lower() if "address" in df.columns else pd.Series("", index=df.index)
        
        # Check any of the normalized terms
        exact_match = pd.Series(False, index=df.index)
        for term in location_terms:
            exact_match |= (loc_col.str.contains(term, regex=False, na=False) | 
                           addr_col.str.contains(term, regex=False, na=False))
        
        signal = signal.where(~exact_match, other=1.0)

    if district:
        # Normalize district as well
        district_terms = _normalize_location(district)
        dist_col = df["district"].fillna("").str.lower()
        
        # Check any of the normalized terms
        district_match = pd.Series(False, index=df.index)
        for term in district_terms:
            district_match |= dist_col.str.contains(term, regex=False, na=False)
        
        # Only apply district score where location score isn't already 1.0
        signal = signal.where(~(district_match & (signal < 1.0)), other=0.5)

    return signal


def _signal_bedrooms(df: pd.DataFrame, requirements: ParsedRequirements) -> pd.Series:
    """Exact bedroom count = 1.0, within ±1 = 0.5, otherwise = 0.0."""
    required = requirements.bedrooms
    if required is None or "bedrooms" not in df.columns:
        return pd.Series(0.5, index=df.index)  # neutral

    beds = df["bedrooms"]
    exact = beds == required
    close = (beds - required).abs() <= 1
    signal = pd.Series(0.0, index=df.index)
    signal = signal.where(~close, other=0.5)
    signal = signal.where(~exact, other=1.0)
    return signal.where(beds.notna(), other=0.0)


def _signal_verified(df: pd.DataFrame) -> pd.Series:
    """1.0 for verified listings, 0.0 otherwise."""
    if "is_verified" not in df.columns:
        return pd.Series(0.0, index=df.index)
    return df["is_verified"].fillna(False).astype(float)


def _signal_size(df: pd.DataFrame, requirements: ParsedRequirements) -> pd.Series:
    """Score how well property size meets stated minimum requirements."""
    intent = requirements.intent

    # For land-related intents, use land_size_perches
    if intent in {Intent.BUY_LAND, Intent.LAND_AND_HOUSE}:
        min_size = requirements.land_size_perches or requirements.minimum_land_size_perches
        col_name = "land_size_perches"
    else:
        min_size = requirements.minimum_house_size_sqft
        col_name = "house_size_sqft"

    if min_size is None or min_size <= 0 or col_name not in df.columns:
        return pd.Series(0.5, index=df.index)

    col = df[col_name]

    # Ratio of actual size to minimum – capped at 2× (no further benefit beyond 2×)
    ratio = (col / min_size).clip(upper=2.0)
    return (ratio / 2.0).where(col.notna(), other=0.0)


def _signal_recency(df: pd.DataFrame) -> pd.Series:
    """Normalise posted_date so the most recent listing = 1.0, oldest = 0.0."""
    if "posted_date" not in df.columns:
        return pd.Series(0.5, index=df.index)

    dates = pd.to_datetime(df["posted_date"], errors="coerce")
    min_ts = dates.min()
    max_ts = dates.max()

    if pd.isna(min_ts) or min_ts == max_ts:
        return pd.Series(0.5, index=df.index)

    span = (max_ts - min_ts).total_seconds()
    normalised = (dates - min_ts).dt.total_seconds() / span
    return normalised.fillna(0.0)


# ── Public API ────────────────────────────────────────────────────────────────

def score_dataframe(df: pd.DataFrame, requirements: ParsedRequirements) -> pd.DataFrame:
    """Add ``score`` and ``score_breakdown`` columns; return sorted descending.

    Args:
        df: Filtered property DataFrame (output of ``apply_hard_filters``).
        requirements: Structured requirements from Agent 1.

    Returns:
        A copy of *df* with two extra columns:
        - ``score`` (float, 0.0 – 1.0)
        - ``score_breakdown`` (JSON string with per-signal contributions)
        Rows are sorted by ``score`` descending.
    """
    out = df.copy()

    s_budget = _signal_budget(out, requirements)
    s_location = _signal_location(out, requirements)
    s_bedrooms = _signal_bedrooms(out, requirements)
    s_verified = _signal_verified(out)
    s_size = _signal_size(out, requirements)
    s_recency = _signal_recency(out)

    out["score"] = (
        _W_BUDGET * s_budget
        + _W_LOCATION * s_location
        + _W_BEDROOMS * s_bedrooms
        + _W_VERIFIED * s_verified
        + _W_SIZE * s_size
        + _W_RECENCY * s_recency
    ).round(4)

    # Store per-signal contributions (weighted) for transparency
    breakdown_df = pd.DataFrame(
        {
            "budget_fit": (_W_BUDGET * s_budget).round(4),
            "location": (_W_LOCATION * s_location).round(4),
            "bedrooms": (_W_BEDROOMS * s_bedrooms).round(4),
            "verified": (_W_VERIFIED * s_verified).round(4),
            "size_fit": (_W_SIZE * s_size).round(4),
            "recency": (_W_RECENCY * s_recency).round(4),
        },
        index=out.index,
    )
    out["score_breakdown"] = breakdown_df.apply(lambda row: row.to_dict(), axis=1)

    return out.sort_values("score", ascending=False)
