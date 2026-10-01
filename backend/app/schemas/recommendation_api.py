"""Public input is user intent only; upstream response types appear in output only."""
from math import isfinite
from typing import Any

from pydantic import ConfigDict, Field, model_validator

from app.schemas.requirements import ParsedRequirements
from app.schemas.recommendation import Contract, RecommendationResponse
from app.schemas.planning import LandHouseOption, PlanningResponse
from app.schemas.property import PropertyResult

SUPPORTED_INTENTS = {"BUY_PROPERTY", "RENT_PROPERTY", "BUY_LAND",
                     "COMPARE_PROPERTIES", "LAND_AND_HOUSE", "PLAN_HOUSE"}


class ConfirmedRequirements(ParsedRequirements):
    model_config = ConfigDict(extra="forbid", use_enum_values=True, allow_inf_nan=False)

    @model_validator(mode="after")
    def public_bounds(self):
        if self.intent not in SUPPORTED_INTENTS:
            raise ValueError("Unsupported recommendation intent")
        if not self.original_query.strip():
            raise ValueError("Original request must not be blank")
        for name, value in self.model_dump().items():
            if isinstance(value, str) and len(value) > (4000 if name == "original_query" else 200):
                raise ValueError("Requirement text exceeds the supported length")
            if isinstance(value, (float, int)) and not isinstance(value, bool):
                if value < 0 or value > 10**15 or (isinstance(value, float) and not isfinite(value)):
                    raise ValueError("Requirement numbers must be finite, nonnegative and within supported bounds")
        if len(self.preferences) > 30 or len(self.missing_information) > 30:
            raise ValueError("Too many requirement values")
        if any(len(s) > 200 for s in self.preferences + self.missing_information):
            raise ValueError("Requirement value is too long")
        for name, low, high in (("bedrooms", 1, 20), ("bathrooms", 1, 20), ("floors", 1, 5), ("parking_spaces", 0, 10)):
            value = getattr(self, name)
            if value is not None and not low <= value <= high:
                raise ValueError(f"{name} is outside the supported range")
        for name in ("land_size_perches", "minimum_land_size_perches", "maximum_land_size_perches", "minimum_house_size_sqft"):
            value = getattr(self, name)
            if value is not None and value <= 0:
                raise ValueError("Requested sizes must be positive")
        for lower, upper in ((self.minimum_budget_lkr, self.maximum_budget_lkr),
                             (self.minimum_land_size_perches, self.maximum_land_size_perches)):
            if lower is not None and upper is not None and lower > upper:
                raise ValueError("Minimum cannot exceed maximum")
        if (self.intent == "RENT_PROPERTY" and self.listing_type == "sale") or (
                self.intent in {"BUY_PROPERTY", "BUY_LAND", "LAND_AND_HOUSE"} and self.listing_type == "rent"):
            raise ValueError("Intent conflicts with listing type")
        return self


class OwnedLandInput(Contract):
    land_width_ft: float | None = Field(default=None, gt=0, le=10000)
    land_length_ft: float | None = Field(default=None, gt=0, le=10000)
    road_side: str | None = Field(default=None, max_length=40)


class RecommendationRequest(Contract):
    requirements: ConfirmedRequirements
    top_k: int = Field(default=3, ge=1, le=10, strict=True)
    explanation_enabled: bool = Field(default=True, strict=True)
    owned_land: OwnedLandInput | None = None

    @model_validator(mode="after")
    def workflow_inputs(self):
        if self.owned_land is not None and self.requirements.intent != "PLAN_HOUSE":
            raise ValueError("Owned-land inputs are only valid for PLAN_HOUSE")
        return self


class RetrievalDisplay(Contract):
    total_found: int
    returned: int
    relaxed_filters: bool
    warnings: list[str]
    filters_applied: dict[str, Any]
    analysis: dict[str, Any]
    metadata: dict[str, Any]


class RecommendationPresentation(Contract):
    properties: list[PropertyResult] = Field(default_factory=list)
    retrieval: RetrievalDisplay | None = None
    land_house_options: list[LandHouseOption] = Field(default_factory=list)
    owned_plan: PlanningResponse | None = None


class RecommendationAPIResponse(RecommendationResponse):
    presentation: RecommendationPresentation = Field(default_factory=RecommendationPresentation)
    clarification_fields: list[str] = Field(default_factory=list)
