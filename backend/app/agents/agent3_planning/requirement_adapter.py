from app.schemas.planning import PlanningRequest, SelectedPropertyContext
from app.schemas.requirements import ParsedRequirements


def planning_request_from_requirements(
    requirements: ParsedRequirements,
    selected_property: SelectedPropertyContext | dict | None = None,
    candidate_count: int = 10,
) -> PlanningRequest:
    return PlanningRequest(
        intent=requirements.intent,
        selected_property=selected_property,
        location=requirements.location,
        land_size_perches=requirements.land_size_perches,
        total_project_budget_lkr=requirements.total_project_budget_lkr,
        construction_budget_lkr=requirements.construction_budget_lkr,
        bedrooms=requirements.bedrooms,
        bathrooms=requirements.bathrooms,
        floors=requirements.floors,
        parking_spaces=requirements.parking_spaces,
        preferred_style=requirements.preferred_style,
        finish_level=requirements.finish_level,
        office_required=requirements.office_required,
        balcony_required=requirements.balcony_required,
        family_lounge_required=requirements.family_lounge_required,
        utility_room_required=requirements.utility_room_required,
        other_requirements=requirements.preferences,
        candidate_count=candidate_count,
    )

