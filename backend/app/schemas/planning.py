from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.requirements import Intent
from app.schemas.requirements import ParsedRequirements


class SelectedPropertyContext(BaseModel):
    listing_id: str | None = None
    location: str | None = None
    district: str | None = None
    property_type: str | None = None
    land_size_perches: float | None = Field(default=None, gt=0)
    land_price_lkr: float | None = Field(default=None, ge=0)
    land_width_ft: float | None = Field(default=None, gt=0)
    land_length_ft: float | None = Field(default=None, gt=0)
    road_side: str | None = None
    source_score: float | None = None


class PlanningRequest(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    intent: Intent
    selected_property: dict[str, Any] | SelectedPropertyContext | None = None
    location: str | None = None
    land_size_perches: float | None = Field(default=None, gt=0)
    land_width_ft: float | None = Field(default=None, gt=0)
    land_length_ft: float | None = Field(default=None, gt=0)
    road_side: str | None = None
    total_project_budget_lkr: float | None = Field(default=None, ge=0)
    construction_budget_lkr: float | None = Field(default=None, ge=0)
    bedrooms: int | None = Field(default=None, ge=1, le=20)
    bathrooms: int | None = Field(default=None, ge=1, le=20)
    floors: int | None = Field(default=None, ge=1, le=5)
    parking_spaces: int | None = Field(default=None, ge=0, le=10)
    preferred_style: str | None = None
    finish_level: str | None = None
    office_required: bool | None = None
    balcony_required: bool | None = None
    family_lounge_required: bool | None = None
    utility_room_required: bool | None = None
    other_requirements: list[str] = Field(default_factory=list)
    candidate_count: int = Field(default=10, ge=1, le=30)

    @field_validator("other_requirements")
    @classmethod
    def limit_other_requirements(cls, value: list[str]) -> list[str]:
        return [item.strip()[:200] for item in value if item.strip()]


class PlanFileSet(BaseModel):
    json: str | None = None
    svg: list[str] = Field(default_factory=list)
    png: list[str] = Field(default_factory=list)
    dxf: str | None = None
    zip: str | None = None
    summary: str | None = None


class PlanningResponse(BaseModel):
    plan_id: str
    constraints_satisfied: bool
    exact_site_fit_verified: bool
    selected_property: SelectedPropertyContext | None = None
    estimated_floor_area_sqft: float | None = None
    layout_score: float | None = None
    score_breakdown: dict[str, float] = Field(default_factory=dict)
    remaining_construction_budget_lkr: float | None = None
    budget_estimation_available: bool = False
    budget_status: str = "COST_DATA_UNAVAILABLE"
    floor_area_estimate: dict[str, Any] | None = None
    construction_cost_estimate: dict[str, Any] | None = None
    total_project_estimate: dict[str, Any] | None = None
    assumptions: list[str] = Field(default_factory=list)
    cost_disclaimer: str | None = None
    warnings: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    plan: dict[str, Any] | None = None
    files: PlanFileSet = Field(default_factory=PlanFileSet)
    disclaimer: str


class LandHouseEvaluationRequest(BaseModel):
    requirements: ParsedRequirements
    property_results: list[dict[str, Any]] = Field(default_factory=list)


class LandHouseOption(BaseModel):
    option_id: str
    property: dict[str, Any]
    house: dict[str, Any]
    budget: dict[str, Any]
    planning: dict[str, Any]
    combination_score: float
    warnings: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    cost_disclaimer: str | None = None
    technical_data: dict[str, Any] = Field(default_factory=dict)


class LandHouseEvaluationResponse(BaseModel):
    options: list[LandHouseOption] = Field(default_factory=list)
    returned: int
    budget_estimation_available: bool
    warnings: list[str] = Field(default_factory=list)
    cost_disclaimer: str | None = None
