import pandas as pd

from app.retrieval.scorer import score_dataframe
from app.schemas.requirements import Intent, ParsedRequirements


def test_scorer_budget_fit() -> None:
    data = [
        {"listing_id": "1", "sale_total_price_lkr": 28_000_000},  # Close to ceiling
        {"listing_id": "2", "sale_total_price_lkr": 15_000_000},  # Much cheaper
    ]
    df = pd.DataFrame(data)

    req = ParsedRequirements(
        original_query="test",
        intent=Intent.BUY_PROPERTY,
        listing_type="sale",
        maximum_budget_lkr=30_000_000,
    )
    
    scored = score_dataframe(df, req)
    
    # Cheaper property should have a higher score (better budget fit)
    assert scored.iloc[0]["listing_id"] == "2"
    assert scored.iloc[0]["score"] > scored.iloc[1]["score"]
    
    # Ensure scores are normalized properly
    assert 0 <= scored.iloc[0]["score"] <= 1.0


def test_scorer_verified_bonus() -> None:
    data = [
        {"listing_id": "unverified", "sale_total_price_lkr": 20_000_000, "is_verified": False},
        {"listing_id": "verified", "sale_total_price_lkr": 20_000_000, "is_verified": True},
    ]
    df = pd.DataFrame(data)

    req = ParsedRequirements(
        original_query="test",
        intent=Intent.BUY_PROPERTY,
        listing_type="sale",
        maximum_budget_lkr=30_000_000,
    )
    
    scored = score_dataframe(df, req)
    
    # Identical properties, verified should score higher
    assert scored.iloc[0]["listing_id"] == "verified"
    assert scored.iloc[1]["listing_id"] == "unverified"
    
    breakdown_verified = scored.iloc[0]["score_breakdown"]
    assert breakdown_verified["verified"] > 0


def test_scorer_location_match() -> None:
    data = [
        {"listing_id": "exact", "location": "Kottawa", "district": "Colombo", "sale_total_price_lkr": 20_000_000},
        {"listing_id": "district", "location": "Malabe", "district": "Colombo", "sale_total_price_lkr": 20_000_000},
        {"listing_id": "none", "location": "Kandy", "district": "Kandy", "sale_total_price_lkr": 20_000_000},
    ]
    df = pd.DataFrame(data)

    req = ParsedRequirements(
        original_query="test",
        intent=Intent.BUY_PROPERTY,
        listing_type="sale",
        location="Kottawa",
        district="Colombo",
    )
    
    scored = score_dataframe(df, req)
    
    # 1st exact location, 2nd district match, 3rd no match
    assert scored.iloc[0]["listing_id"] == "exact"
    assert scored.iloc[1]["listing_id"] == "district"
    assert scored.iloc[2]["listing_id"] == "none"

    b_exact = scored.iloc[0]["score_breakdown"]["location"]
    b_district = scored.iloc[1]["score_breakdown"]["location"]
    b_none = scored.iloc[2]["score_breakdown"]["location"]
    
    assert b_exact > b_district > b_none

