from pathlib import Path

from fastapi import APIRouter

from app.agents.agent3_planning.agent import HomePlanningAgent
from app.agents.agent3_planning.budget import COST_DISCLAIMER, evaluate_land_house_options, planning_request_from_requirements
from app.agents.agent3_planning.budget_document import write_budget_documents
from app.schemas.planning import LandHouseEvaluationRequest, LandHouseEvaluationResponse, PlanningRequest, PlanningResponse

router = APIRouter(prefix="/planning", tags=["planning"])


@router.post("/generate", response_model=PlanningResponse)
def generate_plan(request: PlanningRequest) -> PlanningResponse:
    return HomePlanningAgent().generate(request)


@router.post("/evaluate-land-house", response_model=LandHouseEvaluationResponse)
def evaluate_land_house(request: LandHouseEvaluationRequest) -> LandHouseEvaluationResponse:
    evaluated = evaluate_land_house_options(request.requirements, request.property_results)
    options = [_combined_option(request, option) for option in evaluated[:10]]
    warnings = []
    if not options:
        warnings.append("No land candidates were available to evaluate.")
    elif not any(option.get("budget", {}).get("construction_estimate") for option in options):
        warnings.append("Construction cost configuration is required before numeric land + house estimates can be shown.")
    return LandHouseEvaluationResponse(
        options=options,
        returned=len(options),
        budget_estimation_available=any(option.get("budget", {}).get("construction_estimate") is not None for option in options),
        warnings=warnings,
        cost_disclaimer=COST_DISCLAIMER,
    )


def _combined_option(request: LandHouseEvaluationRequest, option: dict):
    source_property = option.get("source_property") or {}
    plan_request = planning_request_from_requirements(request.requirements, selected_property=source_property)
    plan_response = HomePlanningAgent().generate(plan_request)

    property_data = {
        "listing_id": option.get("listing_id"),
        "title": source_property.get("title"),
        "location": option.get("location"),
        "district": option.get("district"),
        "address": source_property.get("address"),
        "contact_number": source_property.get("contact_number"),
        "land_size_perches": option.get("land_size_perches"),
        "land_price_lkr": option.get("land_price_lkr"),
        "is_verified": source_property.get("is_verified"),
        "agent2_score": option.get("agent2_property_score"),
        "features": _features(source_property.get("features")),
        "full_ad": source_property,
    }
    budget = {
        "total_project_budget_lkr": option.get("total_project_budget_lkr"),
        "land_price_lkr": option.get("land_price_lkr"),
        "remaining_after_land_lkr": option.get("remaining_construction_budget_lkr"),
        "construction_estimate": option.get("construction_estimate"),
        "construction_low_lkr": _nested(option, "construction_estimate", "low_lkr"),
        "construction_expected_lkr": _nested(option, "construction_estimate", "expected_lkr"),
        "construction_high_lkr": _nested(option, "construction_estimate", "high_lkr"),
        "total_project_estimate": option.get("total_project_estimate"),
        "total_low_lkr": _nested(option, "total_project_estimate", "low_lkr"),
        "total_expected_lkr": _nested(option, "total_project_estimate", "expected_lkr"),
        "total_high_lkr": _nested(option, "total_project_estimate", "high_lkr"),
        "expected_margin_lkr": option.get("budget_margin_expected_lkr"),
        "budget_status": option.get("budget_status"),
        "not_included": option.get("not_included", []),
    }
    planning = {
        "plan_id": plan_response.plan_id,
        "constraints_satisfied": plan_response.constraints_satisfied,
        "exact_site_fit_verified": plan_response.exact_site_fit_verified,
        "layout_score": plan_response.layout_score,
        "svg_url": plan_response.files.svg[0] if plan_response.files.svg else None,
        "svg_urls": plan_response.files.svg,
        "png_url": plan_response.files.png[0] if plan_response.files.png else None,
        "png_urls": plan_response.files.png,
        "dxf_url": plan_response.files.dxf,
        "zip_url": plan_response.files.zip,
        "json_url": plan_response.files.json,
        "space_efficiency": (plan_response.plan or {}).get("space_metrics", {}).get("space_efficiency_score") if plan_response.plan else None,
    }
    warnings = option.get("assumptions", []) + option.get("warnings", []) + plan_response.warnings
    combined = {
        "option_id": option.get("option_id"),
        "property": property_data,
        "house": option.get("house", {}),
        "budget": budget,
        "planning": planning,
        "combination_score": option.get("combination_score", 0),
        "warnings": warnings,
        "assumptions": option.get("assumptions", []),
        "cost_disclaimer": option.get("cost_disclaimer"),
        "technical_data": option,
    }
    if plan_response.files.json:
        docs = write_budget_documents(Path(plan_response.files.json).parent, combined, plan_response)
        combined["planning"].update(docs)
    return combined


def _nested(data: dict, parent: str, key: str):
    value = data.get(parent)
    return value.get(key) if isinstance(value, dict) else None


def _features(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [item.strip() for item in str(value).split(",") if item.strip()]
