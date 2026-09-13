"""Hard filter functions for Agent 2 Property Search.

Each function accepts a DataFrame and a ParsedRequirements instance and
returns a boolean Series (mask).  All filters are *skipped* when the
corresponding requirement field is ``None`` so that missing user input
never wrongly excludes listings.

``apply_hard_filters`` chains all applicable filters.  When ``relax=True``
the budget ceiling is expanded by 20 % and the bedroom minimum is dropped,
giving the two-pass fallback a chance to surface results for tight queries.
"""

from __future__ import annotations

import re

import pandas as pd

from app.schemas.requirements import Intent, ParsedRequirements

_BUDGET_RELAX_FACTOR = 1.20  # +20 % on max budget in relaxed mode


# ---------------------------------------------------------------------------
# Individual filter masks
# ---------------------------------------------------------------------------

def _mask_listing_type(df: pd.DataFrame, requirements: ParsedRequirements) -> pd.Series:
    if requirements.listing_type is None:
        return pd.Series(True, index=df.index)
    return df["listing_type"].str.lower() == str(requirements.listing_type).lower()


def _mask_property_type(df: pd.DataFrame, requirements: ParsedRequirements) -> pd.Series:
    """Map intent to acceptable CSV property_type values when no explicit type set."""
    prop_type = requirements.property_type

    # For LAND_AND_HOUSE intent, always search for land listings
    if requirements.intent == Intent.LAND_AND_HOUSE:
        return df["property_type"].str.lower() == "land"

    if prop_type is None:
        return pd.Series(True, index=df.index)

    prop_str = str(prop_type).lower()

    # Map schema enum values to CSV values
    csv_equivalents: dict[str, list[str]] = {
        "house": ["house", "villa", "bungalow"],
        "apartment": ["apartment", "flat", "condo", "holiday_rental"],
        "land": ["land", "plot"],
        "commercial": ["commercial", "warehouse", "office"],
        "room_annex": ["room_annex", "room", "annex"],
        "other": ["other"],
    }
    allowed = csv_equivalents.get(prop_str, [prop_str])
    return df["property_type"].str.lower().isin(allowed)


def _mask_location(df: pd.DataFrame, requirements: ParsedRequirements) -> pd.Series:
    """Match location or district against CSV location, district, and address columns.

    Matching is case-insensitive substring search so 'Kottawa' matches
    'kottawa road dolekade' in the address column.
    """
    location = requirements.location
    district = requirements.district

    if location is None and district is None:
        return pd.Series(True, index=df.index)

    mask = pd.Series(False, index=df.index)

    for req_val in filter(None, [location, district]):
        pattern = re.escape(req_val.strip())
        for col in ("location", "district", "address"):
            if col in df.columns:
                col_str = df[col].fillna("").str
                mask |= col_str.contains(pattern, case=False, regex=True, na=False)

    return mask


def _mask_max_budget(
    df: pd.DataFrame,
    requirements: ParsedRequirements,
    relax: bool = False,
) -> pd.Series:
    budget = requirements.maximum_land_budget_lkr if requirements.intent == Intent.LAND_AND_HOUSE else requirements.maximum_budget_lkr
    if budget is None:
        return pd.Series(True, index=df.index)

    effective_budget = int(budget * _BUDGET_RELAX_FACTOR) if relax else budget

    listing_type = (requirements.listing_type or "").lower()

    if listing_type == "rent":
        col = df["rent_monthly_lkr"]
    else:
        col = df["sale_total_price_lkr"]

    return col.notna() & (col <= effective_budget)


def _mask_min_budget(df: pd.DataFrame, requirements: ParsedRequirements) -> pd.Series:
    budget = requirements.minimum_budget_lkr
    if budget is None:
        return pd.Series(True, index=df.index)

    listing_type = (requirements.listing_type or "").lower()
    col = df["rent_monthly_lkr"] if listing_type == "rent" else df["sale_total_price_lkr"]
    return col.notna() & (col >= budget)


def _mask_bedrooms(
    df: pd.DataFrame,
    requirements: ParsedRequirements,
    relax: bool = False,
) -> pd.Series:
    if relax or requirements.bedrooms is None:
        return pd.Series(True, index=df.index)
    return df["bedrooms"].notna() & (df["bedrooms"] >= requirements.bedrooms)


def _mask_min_land_size(df: pd.DataFrame, requirements: ParsedRequirements) -> pd.Series:
    # Use minimum_land_size_perches if set, else fall back to land_size_perches as minimum.
    min_size = requirements.minimum_land_size_perches or requirements.land_size_perches
    if min_size is None:
        return pd.Series(True, index=df.index)
    return df["land_size_perches"].notna() & (df["land_size_perches"] >= min_size)


def _mask_max_land_size(df: pd.DataFrame, requirements: ParsedRequirements) -> pd.Series:
    max_size = requirements.maximum_land_size_perches
    if max_size is None:
        return pd.Series(True, index=df.index)
    return df["land_size_perches"].notna() & (df["land_size_perches"] <= max_size)


def _mask_min_house_size(df: pd.DataFrame, requirements: ParsedRequirements) -> pd.Series:
    min_size = requirements.minimum_house_size_sqft
    if min_size is None:
        return pd.Series(True, index=df.index)
    return df["house_size_sqft"].notna() & (df["house_size_sqft"] >= min_size)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def apply_hard_filters(
    df: pd.DataFrame,
    requirements: ParsedRequirements,
    relax: bool = False,
) -> pd.DataFrame:
    """Return a filtered DataFrame keeping only listings that satisfy all hard filters.

    Args:
        df: Full property dataset.
        requirements: Structured requirements from Agent 1.
        relax: When *True*, the budget ceiling is expanded by 20 % and the
            bedroom minimum is dropped.  Used for the two-pass fallback.

    Returns:
        Filtered DataFrame (may be empty).
    """
    mask = pd.Series(True, index=df.index)

    mask &= _mask_listing_type(df, requirements)
    mask &= _mask_property_type(df, requirements)
    mask &= _mask_location(df, requirements)
    mask &= _mask_max_budget(df, requirements, relax=relax)
    mask &= _mask_min_budget(df, requirements)
    mask &= _mask_bedrooms(df, requirements, relax=relax)
    mask &= _mask_min_land_size(df, requirements)
    mask &= _mask_max_land_size(df, requirements)
    mask &= _mask_min_house_size(df, requirements)

    return df[mask].copy()


def describe_filters(requirements: ParsedRequirements, relax: bool = False) -> dict:
    """Return a human-readable snapshot of which filters were applied."""
    budget = requirements.maximum_land_budget_lkr if requirements.intent == Intent.LAND_AND_HOUSE else requirements.maximum_budget_lkr
    return {
        "listing_type": requirements.listing_type,
        "property_type": requirements.property_type,
        "location": requirements.location,
        "district": requirements.district,
        "max_budget_lkr": int(budget * _BUDGET_RELAX_FACTOR) if (budget and relax) else budget,
        "max_land_budget_lkr": requirements.maximum_land_budget_lkr,
        "total_project_budget_lkr": requirements.total_project_budget_lkr,
        "min_budget_lkr": requirements.minimum_budget_lkr,
        "bedrooms_min": None if relax else requirements.bedrooms,
        "land_size_perches_min": requirements.minimum_land_size_perches or requirements.land_size_perches,
        "land_size_perches_max": requirements.maximum_land_size_perches,
        "house_size_sqft_min": requirements.minimum_house_size_sqft,
        "relaxed": relax,
    }
