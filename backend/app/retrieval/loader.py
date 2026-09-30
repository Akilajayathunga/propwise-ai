"""Dataset loader for Agent 2.

Resolves the dataset path in priority order:
  1. ``path`` argument (explicit override)
  2. ``CLEANED_DATASET_PATH`` environment variable
  3. ``data/sample/properties_sample.csv`` (Git-tracked fallback for dev/tests)

The DataFrame is cached in memory after the first load so repeated calls
within the same process pay no I/O cost.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import pandas as pd

from app.retrieval.contact import NOT_MENTIONED, extract_contact_number

# Columns that must be numeric; missing / unparseable values become NaN.
_NUMERIC_COLUMNS = [
    "price_lkr",
    "sale_total_price_lkr",
    "rent_monthly_lkr",
    "bedrooms",
    "bathrooms",
    "land_size_perches",
    "house_size_sqft",
    "property_size_sqft",
]

_PROJECT_ROOT = Path(__file__).resolve().parents[3]  # …/propwise-ai
_FALLBACK_PATH = _PROJECT_ROOT / "data" / "sample" / "properties_sample.csv"


def _resolve_path(path: str | None) -> Path:
    if path:
        return Path(path)
    env_path = os.getenv("CLEANED_DATASET_PATH") or os.getenv("PROPERTY_DATASET_PATH")
    if env_path:
        return Path(env_path)
    return _FALLBACK_PATH


def _normalise(df: pd.DataFrame) -> pd.DataFrame:
    """Cast columns to consistent types so downstream code never has to guess."""
    # Numeric columns
    for col in _NUMERIC_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Boolean column
    if "is_verified" in df.columns:
        df["is_verified"] = df["is_verified"].map(
            lambda v: str(v).strip().lower() in {"true", "1", "yes"}
        )

    # String columns – fill NaN with None (keeps downstream isinstance checks clean)
    str_cols = [
        "listing_id", "title", "description", "listing_type", "property_type",
        "district", "location", "address", "price_basis", "land_type",
        "property_subtype", "features", "posted_date", "deactivation_date",
        "geo_region", "membership_level", "member_since", "contact_number",
    ]
    for col in str_cols:
        if col in df.columns:
            df[col] = df[col].where(df[col].notna(), other=None)

    if "contact_number" not in df.columns:
        df["contact_number"] = df.apply(
            lambda row: extract_contact_number(
                row.get("description"),
                row.get("title"),
                row.get("address"),
                row.get("features"),
            ),
            axis=1,
        )
    else:
        df["contact_number"] = df.apply(
            lambda row: row.get("contact_number")
            if row.get("contact_number") not in {None, ""}
            else extract_contact_number(row.get("description"), row.get("title"), row.get("address"), row.get("features")),
            axis=1,
        )
        df["contact_number"] = df["contact_number"].fillna(NOT_MENTIONED)

    return df


@lru_cache(maxsize=1)
def _load_cached(resolved_path: str) -> pd.DataFrame:
    """Internal cached loader – keyed on the resolved absolute path string."""
    df = pd.read_csv(resolved_path, encoding="utf-8", encoding_errors="replace", low_memory=False)
    return _normalise(df)


def load_dataset(path: str | None = None) -> pd.DataFrame:
    """Return the property dataset as a normalised DataFrame.

    The result is cached after the first load.  Pass an explicit *path* to
    override the default resolution order (useful in tests).
    """
    resolved = str(_resolve_path(path).resolve())
    return _load_cached(resolved)


def clear_cache() -> None:
    """Evict the in-memory cache (used in tests that swap datasets)."""
    _load_cached.cache_clear()
