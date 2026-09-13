import json
from pathlib import Path
from typing import Any

from app.agents.agent3_planning.property_adapter import adapt_selected_property
from app.agents.agent3_planning.room_program import build_room_program
from app.schemas.planning import PlanningRequest
from app.schemas.property import PropertyResult
from app.schemas.requirements import Intent, ParsedRequirements

ROOT = Path(__file__).resolve().parents[4]
COSTS_PATH = ROOT / "data" / "knowledge" / "construction_costs.json"

STATUS_ORDER = {
    "WITHIN_BUDGET": 0,
    "POTENTIALLY_FEASIBLE": 1,
    "TIGHT_BUDGET": 2,
    "ABOVE_BUDGET": 3,
    "COST_DATA_UNAVAILABLE": 4,
}

COST_DISCLAIMER = (
    "This is an indicative early-stage construction estimate based on configured cost assumptions "
    "and conceptual floor area. It is not a contractor quotation or professional quantity-surveyor "
    "estimate. Actual construction cost can vary based on design, materials, labour, location, "
    "ground conditions, approvals, market conditions and other factors."
)


class CostConfigurationError(ValueError):
    pass


def analyze_budget(
    request: PlanningRequest,
    selected_property,
    estimated_floor_area_sqft: float,
) -> dict:
    selected = adapt_selected_property(selected_property)
    land_price = selected.land_price_lkr if selected and selected.land_price_lkr is not None else 0
    remaining = request.construction_budget_lkr
    if request.total_project_budget_lkr is not None and selected and selected.land_price_lkr is not None:
        remaining = request.total_project_budget_lkr - selected.land_price_lkr

    area_range = estimate_floor_area_range(request)
    cost_result = estimate_construction_cost(area_range["recommended_floor_area_sqft"], request.finish_level)
    if not cost_result["budget_estimation_available"]:
        return {
            "remaining_construction_budget_lkr": remaining,
            "budget_estimation_available": False,
            "budget_status": "ABOVE_BUDGET" if remaining is not None and remaining <= 0 else "COST_DATA_UNAVAILABLE",
            "construction_cost_estimate": None,
            "floor_area_estimate": area_range,
            "assumptions": cost_result["assumptions"],
            "cost_disclaimer": COST_DISCLAIMER,
        }

    budget = remaining if remaining is not None else request.total_project_budget_lkr
    status = classify_budget_status(
        cost_result["low_lkr"],
        cost_result["expected_lkr"],
        cost_result["high_lkr"],
        budget,
    )
    return {
        "remaining_construction_budget_lkr": remaining,
        "budget_estimation_available": True,
        "budget_status": status,
        "construction_cost_estimate": cost_result,
        "floor_area_estimate": area_range,
        "assumptions": cost_result["assumptions"],
        "cost_disclaimer": COST_DISCLAIMER,
        "total_project_estimate": _total_project_estimate(land_price, cost_result),
    }


def estimate_floor_area_range(request: PlanningRequest) -> dict[str, float]:
    program = build_room_program(request)
    preferred = sum(room.preferred_area for room in program if room.type not in {"parking", "balcony"})
    circulation_allowance = preferred * 0.14
    wall_service_allowance = preferred * 0.08
    recommended = preferred + circulation_allowance + wall_service_allowance
    return {
        "minimum_floor_area_sqft": round(max(1.0, preferred * 0.86), 2),
        "recommended_floor_area_sqft": round(recommended, 2),
        "maximum_floor_area_sqft": round(recommended * 1.18, 2),
        "usable_room_preferred_area_sqft": round(preferred, 2),
        "circulation_allowance_sqft": round(circulation_allowance, 2),
        "wall_service_allowance_sqft": round(wall_service_allowance, 2),
    }


def estimate_construction_cost(floor_area_sqft: float, finish_level: str | None = None, config: dict | None = None) -> dict[str, Any]:
    config = config or _load_cost_config()
    profile_name = _profile_name(config, finish_level)
    try:
        profile = validate_cost_profile(config, profile_name)
    except CostConfigurationError as exc:
        return {
            "budget_estimation_available": False,
            "budget_status": "COST_DATA_UNAVAILABLE",
            "reason": str(exc),
            "assumptions": _unavailable_assumptions(config, profile_name, str(exc)),
        }

    contingency_percent = float(config.get("construction_contingency_percent") or 0)
    low_base = floor_area_sqft * profile["low_rate_per_sqft"]
    expected_base = floor_area_sqft * profile["expected_rate_per_sqft"]
    high_base = floor_area_sqft * profile["high_rate_per_sqft"]

    return {
        "budget_estimation_available": True,
        "profile": profile_name,
        "floor_area_sqft": round(floor_area_sqft, 2),
        "rates_lkr_per_sqft": profile,
        "contingency_percent": contingency_percent,
        "low_base_lkr": round(low_base, 2),
        "expected_base_lkr": round(expected_base, 2),
        "high_base_lkr": round(high_base, 2),
        "low_contingency_lkr": round(low_base * contingency_percent / 100, 2),
        "expected_contingency_lkr": round(expected_base * contingency_percent / 100, 2),
        "high_contingency_lkr": round(high_base * contingency_percent / 100, 2),
        "low_lkr": round(low_base * (1 + contingency_percent / 100), 2),
        "expected_lkr": round(expected_base * (1 + contingency_percent / 100), 2),
        "high_lkr": round(high_base * (1 + contingency_percent / 100), 2),
        "metadata": config.get("metadata", {}),
        "assumptions": [
            f"Construction estimate uses the configured {profile_name} finish profile.",
            "Estimate is based on conceptual floor area from the requested room programme.",
            "Land transfer costs are not included.",
            "Professional fees are not included.",
            "Approval fees, utility connections, furniture and landscaping are not included.",
        ],
    }


def validate_cost_profile(config: dict, profile_name: str) -> dict[str, float]:
    metadata = config.get("metadata") or {}
    if not metadata.get("source") or not metadata.get("effective_date"):
        raise CostConfigurationError("Construction cost metadata source and effective_date are required.")
    profiles = config.get("profiles") or {}
    profile = profiles.get(profile_name)
    if not profile:
        raise CostConfigurationError(f"Construction cost profile '{profile_name}' is missing.")
    values = {
        "low_rate_per_sqft": profile.get("low_rate_per_sqft"),
        "expected_rate_per_sqft": profile.get("expected_rate_per_sqft"),
        "high_rate_per_sqft": profile.get("high_rate_per_sqft"),
    }
    if any(value is None for value in values.values()):
        raise CostConfigurationError(f"Construction cost profile '{profile_name}' has null rates.")
    try:
        rates = {key: float(value) for key, value in values.items()}
    except (TypeError, ValueError) as exc:
        raise CostConfigurationError(f"Construction cost profile '{profile_name}' has malformed rates.") from exc
    if any(value <= 0 for value in rates.values()):
        raise CostConfigurationError(f"Construction cost profile '{profile_name}' rates must be positive.")
    if not rates["low_rate_per_sqft"] <= rates["expected_rate_per_sqft"] <= rates["high_rate_per_sqft"]:
        raise CostConfigurationError(f"Construction cost profile '{profile_name}' must satisfy low <= expected <= high.")
    return rates


def classify_budget_status(low_total: float, expected_total: float, high_total: float, budget: float | None) -> str:
    if budget is None:
        return "COST_DATA_UNAVAILABLE"
    if high_total <= budget:
        return "WITHIN_BUDGET"
    if expected_total <= budget:
        return "POTENTIALLY_FEASIBLE"
    if low_total <= budget:
        return "TIGHT_BUDGET"
    return "ABOVE_BUDGET"


def evaluate_land_house_options(parsed_requirements: ParsedRequirements, property_results: list[PropertyResult | dict]) -> list[dict]:
    request = planning_request_from_requirements(parsed_requirements)
    area_range = estimate_floor_area_range(request)
    construction = estimate_construction_cost(area_range["recommended_floor_area_sqft"], parsed_requirements.finish_level)
    options = []
    for index, prop in enumerate(property_results):
        prop_data = prop.model_dump() if hasattr(prop, "model_dump") else dict(prop)
        selected = adapt_selected_property(prop_data)
        land_price = selected.land_price_lkr if selected and selected.land_price_lkr is not None else prop_data.get("sale_total_price_lkr")
        if land_price is None:
            continue
        remaining = parsed_requirements.total_project_budget_lkr - land_price if parsed_requirements.total_project_budget_lkr is not None else None
        if not construction["budget_estimation_available"]:
            status = "COST_DATA_UNAVAILABLE"
            totals = None
            budget_score = 0.0
        else:
            totals = _total_project_estimate(land_price, construction)
            status = classify_budget_status(totals["low_lkr"], totals["expected_lkr"], totals["high_lkr"], parsed_requirements.total_project_budget_lkr)
            budget_score = _budget_score(status, totals["expected_lkr"], parsed_requirements.total_project_budget_lkr)
        agent2_score = float(prop_data.get("score") or 0)
        land_fit = _land_size_suitability(prop_data.get("land_size_perches"), parsed_requirements.land_size_perches)
        house_fit = _house_program_fit(parsed_requirements)
        combination_score = _combination_score(agent2_score, budget_score, land_fit, house_fit)
        options.append(
            {
                "option_id": f"option-{index + 1}",
                "rank_input_order": index + 1,
                "listing_id": prop_data.get("listing_id"),
                "location": prop_data.get("location"),
                "district": prop_data.get("district"),
                "land_size_perches": prop_data.get("land_size_perches"),
                "land_price_lkr": land_price,
                "total_project_budget_lkr": parsed_requirements.total_project_budget_lkr,
                "remaining_construction_budget_lkr": remaining,
                "house": {
                    "bedrooms": request.bedrooms,
                    "bathrooms": request.bathrooms,
                    "floors": request.floors,
                    "parking_spaces": request.parking_spaces,
                    "estimated_floor_area_sqft": area_range["recommended_floor_area_sqft"],
                    "floor_area_range": area_range,
                },
                "construction_estimate": construction if construction["budget_estimation_available"] else None,
                "total_project_estimate": totals,
                "budget_status": status,
                "budget_margin_expected_lkr": None if not totals or parsed_requirements.total_project_budget_lkr is None else round(parsed_requirements.total_project_budget_lkr - totals["expected_lkr"], 2),
                "budget_margin_high_lkr": None if not totals or parsed_requirements.total_project_budget_lkr is None else round(parsed_requirements.total_project_budget_lkr - totals["high_lkr"], 2),
                "agent2_property_score": agent2_score,
                "budget_score": budget_score,
                "land_size_suitability_score": land_fit,
                "house_program_fit_score": house_fit,
                "combination_score": combination_score,
                "assumptions": planning_assumptions(parsed_requirements) + construction.get("assumptions", []),
                "cost_disclaimer": COST_DISCLAIMER,
                "not_included": ["Land transfer costs", "Professional fees", "Approval fees", "Utility connections", "Furniture", "Landscaping"],
                "source_property": prop_data,
            }
        )
    return sorted(options, key=lambda option: (STATUS_ORDER.get(option["budget_status"], 99), -option["combination_score"]))


def planning_request_from_requirements(requirements: ParsedRequirements, selected_property: dict | None = None) -> PlanningRequest:
    return PlanningRequest(
        intent=Intent.LAND_AND_HOUSE,
        selected_property=selected_property,
        location=requirements.location,
        land_size_perches=requirements.land_size_perches,
        total_project_budget_lkr=requirements.total_project_budget_lkr,
        construction_budget_lkr=requirements.construction_budget_lkr,
        bedrooms=requirements.bedrooms or 3,
        bathrooms=requirements.bathrooms or _default_bathrooms(requirements.bedrooms),
        floors=requirements.floors or 1,
        parking_spaces=requirements.parking_spaces or 1,
        preferred_style=requirements.preferred_style,
        finish_level=requirements.finish_level,
        office_required=requirements.office_required,
        balcony_required=requirements.balcony_required,
        family_lounge_required=requirements.family_lounge_required,
        utility_room_required=requirements.utility_room_required,
    )


def planning_assumptions(requirements: ParsedRequirements) -> list[str]:
    assumptions = []
    if requirements.bedrooms is None:
        assumptions.append("3 bedrooms assumed because bedroom count was not specified.")
    if requirements.bathrooms is None:
        assumptions.append(f"{_default_bathrooms(requirements.bedrooms)} bathroom(s) assumed for conceptual planning.")
    if requirements.floors is None:
        assumptions.append("1 floor assumed because floor count was not specified.")
    if requirements.parking_spaces is None:
        assumptions.append("1 parking space assumed for conceptual planning.")
    return assumptions


def _default_bathrooms(bedrooms: int | None) -> int:
    if bedrooms is None:
        return 2
    if bedrooms <= 2:
        return 1
    return 2


def _total_project_estimate(land_price: float, construction: dict) -> dict[str, float]:
    return {
        "land_price_lkr": round(land_price, 2),
        "low_lkr": round(land_price + construction["low_lkr"], 2),
        "expected_lkr": round(land_price + construction["expected_lkr"], 2),
        "high_lkr": round(land_price + construction["high_lkr"], 2),
    }


def _budget_score(status: str, expected_total: float, budget: float | None) -> float:
    base = {"WITHIN_BUDGET": 100, "POTENTIALLY_FEASIBLE": 82, "TIGHT_BUDGET": 55, "ABOVE_BUDGET": 18}.get(status, 0)
    if budget is None or budget <= 0:
        return float(base)
    margin_ratio = max(-1.0, min(1.0, (budget - expected_total) / budget))
    return round(max(0.0, min(100.0, base + margin_ratio * 12)), 2)


def _land_size_suitability(size: float | None, requested_min: float | None) -> float:
    if size is None:
        return 50.0
    target = requested_min or 8.0
    if size >= target:
        return min(100.0, 78.0 + min(22.0, (size - target) * 2.2))
    return max(20.0, 78.0 - (target - size) * 8.0)


def _house_program_fit(requirements: ParsedRequirements) -> float:
    score = 65.0
    if requirements.bedrooms:
        score += min(18.0, requirements.bedrooms * 4)
    if requirements.bathrooms:
        score += min(10.0, requirements.bathrooms * 2)
    if requirements.floors:
        score += 4.0
    return min(100.0, score)


def _combination_score(agent2_score: float, budget_score: float, land_fit: float, house_fit: float) -> float:
    config = _load_cost_config()
    weights = config.get("combination_score_weights") or {}
    return round(
        agent2_score * 100 * float(weights.get("agent2_land_match", 0.35))
        + budget_score * float(weights.get("budget_feasibility", 0.35))
        + land_fit * float(weights.get("land_size_suitability", 0.15))
        + house_fit * float(weights.get("house_program_fit", 0.15)),
        2,
    )


def _profile_name(config: dict, finish_level: str | None) -> str:
    if finish_level in {"basic", "standard", "premium"}:
        return finish_level
    return str(config.get("default_profile") or "standard")


def _unavailable_assumptions(config: dict, profile_name: str, reason: str) -> list[str]:
    return [
        f"Construction cost configuration is required for the {profile_name} finish profile.",
        reason,
        "Populate low_rate_per_sqft, expected_rate_per_sqft and high_rate_per_sqft with sourced positive values.",
        "Populate metadata.source and metadata.effective_date before using estimates.",
    ]


def _load_cost_config() -> dict:
    with COSTS_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)
