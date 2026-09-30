import json

import pytest

from app.agents.agent3_planning import budget
from app.agents.agent3_planning.budget import (
    CostConfigurationError,
    classify_budget_status,
    estimate_construction_cost,
    estimate_floor_area_range,
    evaluate_land_house_options,
    validate_cost_profile,
)
from app.schemas.planning import PlanningRequest
from app.schemas.requirements import Intent, ParsedRequirements


VALID_CONFIG = {
    "currency": "LKR",
    "unit": "sqft",
    "default_profile": "standard",
    "construction_contingency_percent": 10,
    "profiles": {
        "standard": {
            "low_rate_per_sqft": 10000,
            "expected_rate_per_sqft": 12000,
            "high_rate_per_sqft": 15000,
        }
    },
    "combination_score_weights": {
        "agent2_land_match": 0.35,
        "budget_feasibility": 0.35,
        "land_size_suitability": 0.15,
        "house_program_fit": 0.15,
    },
    "metadata": {"source": "test fixture", "effective_date": "2026-01-01", "notes": "test only"},
}


def requirements_40m() -> ParsedRequirements:
    return ParsedRequirements(
        original_query="I want to buy land in Kottawa and build a 2-bedroom house. My maximum TOTAL budget is Rs. 40 million.",
        intent=Intent.LAND_AND_HOUSE,
        location="Kottawa",
        bedrooms=2,
        total_project_budget_lkr=40_000_000,
        property_type="land",
        listing_type="sale",
    )


def test_floor_area_uses_house_program() -> None:
    two_bed = estimate_floor_area_range(PlanningRequest(intent=Intent.LAND_AND_HOUSE, bedrooms=2, bathrooms=1, floors=1))
    four_bed = estimate_floor_area_range(PlanningRequest(intent=Intent.LAND_AND_HOUSE, bedrooms=4, bathrooms=3, floors=2))

    assert two_bed["recommended_floor_area_sqft"] > two_bed["minimum_floor_area_sqft"]
    assert four_bed["recommended_floor_area_sqft"] > two_bed["recommended_floor_area_sqft"]


def test_construction_estimate_uses_configured_rate() -> None:
    estimate = estimate_construction_cost(1000, config=VALID_CONFIG)

    assert estimate["low_lkr"] == 11_000_000
    assert estimate["expected_lkr"] == 13_200_000
    assert estimate["high_lkr"] == 16_500_000
    assert estimate["expected_contingency_lkr"] == 1_200_000


def test_feasibility_classification_rules() -> None:
    assert classify_budget_status(10, 20, 30, 40) == "WITHIN_BUDGET"
    assert classify_budget_status(10, 20, 50, 40) == "POTENTIALLY_FEASIBLE"
    assert classify_budget_status(10, 50, 60, 40) == "TIGHT_BUDGET"
    assert classify_budget_status(50, 60, 70, 40) == "ABOVE_BUDGET"


def test_multiple_land_options_rank_feasible_above_unaffordable(tmp_path, monkeypatch) -> None:
    path = tmp_path / "construction_costs.json"
    path.write_text(json.dumps(VALID_CONFIG), encoding="utf-8")
    monkeypatch.setattr(budget, "COSTS_PATH", path)

    options = evaluate_land_house_options(
        requirements_40m(),
        [
            {"listing_id": "expensive", "location": "Kottawa", "property_type": "land", "sale_total_price_lkr": 31_000_000, "land_size_perches": 10, "score": 0.98, "listing_type": "sale", "title": "Expensive Land"},
            {"listing_id": "fit", "location": "Kottawa", "property_type": "land", "sale_total_price_lkr": 12_000_000, "land_size_perches": 10, "score": 0.8, "listing_type": "sale", "title": "Fit Land"},
            {"listing_id": "tight", "location": "Kottawa", "property_type": "land", "sale_total_price_lkr": 24_000_000, "land_size_perches": 8, "score": 0.7, "listing_type": "sale", "title": "Tight Land"},
        ],
    )

    assert options[0]["listing_id"] == "fit"
    assert options[0]["remaining_construction_budget_lkr"] == 28_000_000
    assert options[0]["construction_estimate"]["expected_lkr"] > 0
    assert options[0]["total_project_estimate"]["expected_lkr"] == options[0]["land_price_lkr"] + options[0]["construction_estimate"]["expected_lkr"]
    assert options[0]["agent2_property_score"] == 0.8
    assert options[0]["combination_score"] > 0
    assert options[-1]["budget_status"] == "ABOVE_BUDGET"


def test_missing_cost_data_handled_clearly() -> None:
    estimate = estimate_construction_cost(1000, config={"profiles": {"standard": {"low_rate_per_sqft": None, "expected_rate_per_sqft": None, "high_rate_per_sqft": None}}, "metadata": {}})

    assert estimate["budget_estimation_available"] is False
    assert estimate["budget_status"] == "COST_DATA_UNAVAILABLE"
    assert "Construction cost configuration is required" in estimate["assumptions"][0]


def test_malformed_cost_data_rejected() -> None:
    bad_config = {
        **VALID_CONFIG,
        "profiles": {"standard": {"low_rate_per_sqft": 15000, "expected_rate_per_sqft": 12000, "high_rate_per_sqft": 10000}},
    }

    with pytest.raises(CostConfigurationError):
        validate_cost_profile(bad_config, "standard")


def test_frontend_contains_budget_labels() -> None:
    frontend_js = (budget.ROOT / "frontend" / "app.js").read_text(encoding="utf-8")

    assert "Maximum total budget" in frontend_js
    assert "Land price" in frontend_js
    assert "Construction estimate" in frontend_js
    assert "Expected total" in frontend_js
    assert "View ad details" in frontend_js
    assert "Show budget summary" in frontend_js
    assert "Download plan" in frontend_js
    assert "Download Excel" in frontend_js
    assert "Contact number" in frontend_js
    assert "Seller ad caption" in frontend_js
    assert "All floors ZIP" in frontend_js
