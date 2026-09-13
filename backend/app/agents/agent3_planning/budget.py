import json
from pathlib import Path

from app.schemas.planning import PlanningRequest, SelectedPropertyContext

ROOT = Path(__file__).resolve().parents[4]
COSTS_PATH = ROOT / "data" / "knowledge" / "construction_costs.json"


def analyze_budget(
    request: PlanningRequest,
    selected_property: SelectedPropertyContext | None,
    estimated_floor_area_sqft: float,
) -> dict:
    remaining = request.construction_budget_lkr
    if request.total_project_budget_lkr is not None and selected_property and selected_property.land_price_lkr is not None:
        remaining = request.total_project_budget_lkr - selected_property.land_price_lkr

    if remaining is not None and remaining <= 0:
        return {
            "remaining_construction_budget_lkr": remaining,
            "budget_estimation_available": False,
            "budget_status": "ABOVE_BUDGET",
            "construction_cost_estimate": None,
        }

    config = _load_cost_config()
    if not config.get("verified_rates_available"):
        return {
            "remaining_construction_budget_lkr": remaining,
            "budget_estimation_available": False,
            "budget_status": "COST_DATA_UNAVAILABLE",
            "construction_cost_estimate": None,
        }

    rates = config["rates_lkr_per_sqft"]
    estimate = {
        "low_estimate": round(estimated_floor_area_sqft * rates["low"], 2),
        "expected_estimate": round(estimated_floor_area_sqft * rates["expected"], 2),
        "high_estimate": round(estimated_floor_area_sqft * rates["high"], 2),
    }
    status = "WITHIN_BUDGET" if remaining is None or estimate["expected_estimate"] <= remaining else "ABOVE_BUDGET"
    return {
        "remaining_construction_budget_lkr": remaining,
        "budget_estimation_available": True,
        "budget_status": status,
        "construction_cost_estimate": estimate,
    }


def _load_cost_config() -> dict:
    with COSTS_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)

