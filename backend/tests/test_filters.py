import pandas as pd

from app.retrieval.filters import apply_hard_filters
from app.schemas.requirements import Intent, ParsedRequirements


def test_hard_filters_strict() -> None:
    # Minimal mock dataset
    data = [
        {"listing_type": "sale", "property_type": "house", "location": "Colombo", "sale_total_price_lkr": 25_000_000, "bedrooms": 3},
        {"listing_type": "sale", "property_type": "apartment", "location": "Colombo", "sale_total_price_lkr": 30_000_000, "bedrooms": 2},
        {"listing_type": "rent", "property_type": "house", "location": "Colombo", "rent_monthly_lkr": 100_000, "bedrooms": 3},
        {"listing_type": "sale", "property_type": "house", "location": "Kandy", "sale_total_price_lkr": 15_000_000, "bedrooms": 3},
    ]
    df = pd.DataFrame(data)

    req = ParsedRequirements(
        original_query="test",
        intent=Intent.BUY_PROPERTY,
        listing_type="sale",
        property_type="house",
        location="Colombo",
        maximum_budget_lkr=30_000_000,
        bedrooms=3,
    )
    
    filtered = apply_hard_filters(df, req, relax=False)
    
    assert len(filtered) == 1
    assert filtered.iloc[0]["property_type"] == "house"
    assert filtered.iloc[0]["location"] == "Colombo"
    assert filtered.iloc[0]["listing_type"] == "sale"


def test_hard_filters_relaxed() -> None:
    # Mock dataset where everything is slightly over budget or missing a bedroom
    data = [
        {"listing_type": "sale", "property_type": "house", "location": "Colombo", "sale_total_price_lkr": 32_000_000, "bedrooms": 2},
    ]
    df = pd.DataFrame(data)

    req = ParsedRequirements(
        original_query="test",
        intent=Intent.BUY_PROPERTY,
        listing_type="sale",
        location="Colombo",
        maximum_budget_lkr=30_000_000,  # 32M is over
        bedrooms=3,                     # Need 3, only has 2
    )
    
    strict = apply_hard_filters(df, req, relax=False)
    assert strict.empty
    
    # Relaxed expands budget by 20% (to 36M) and drops bedroom constraint
    relaxed = apply_hard_filters(df, req, relax=True)
    assert len(relaxed) == 1
    assert relaxed.iloc[0]["sale_total_price_lkr"] == 32_000_000


def test_land_and_house_intent_filters_only_land() -> None:
    data = [
        {"listing_type": "sale", "property_type": "house", "location": "Colombo", "sale_total_price_lkr": 25_000_000},
        {"listing_type": "sale", "property_type": "land", "location": "Colombo", "sale_total_price_lkr": 15_000_000},
    ]
    df = pd.DataFrame(data)

    req = ParsedRequirements(
        original_query="test",
        intent=Intent.LAND_AND_HOUSE,
        location="Colombo",
        maximum_budget_lkr=30_000_000,
    )
    
    filtered = apply_hard_filters(df, req)
    assert len(filtered) == 1
    assert filtered.iloc[0]["property_type"] == "land"

