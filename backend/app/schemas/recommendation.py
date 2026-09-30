"""Agent 4 contracts. Scores are decision-support indices, never probabilities."""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.planning import LandHouseEvaluationResponse, PlanningResponse
from app.schemas.property import Agent2Result, PropertyResult
from app.schemas.requirements import ParsedRequirements


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Eligibility(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    CONDITIONAL = "CONDITIONAL"
    HARD_CONSTRAINT_VIOLATION = "HARD_CONSTRAINT_VIOLATION"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class ResponseStatus(str, Enum):
    OK = "OK"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    NO_SUITABLE_OPTION = "NO_SUITABLE_OPTION"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class RecommendationContext(Contract):
    requirements: ParsedRequirements
    property_search: Agent2Result | None = None
    land_house: LandHouseEvaluationResponse | None = None
    owned_land: PlanningResponse | None = None
    top_k: int = Field(default=3, ge=1, le=50)

    @model_validator(mode="after")
    def validate_workflow(self):
        intent = self.requirements.intent
        if intent == "PLAN_HOUSE":
            if self.property_search is not None or self.land_house is not None:
                raise ValueError("Owned-land assessment cannot contain retrieval/combination results")
        elif self.owned_land is not None:
            raise ValueError("Direct planning evidence is only valid for PLAN_HOUSE")
        if intent != "LAND_AND_HOUSE" and self.land_house is not None:
            raise ValueError("Combination evidence requires LAND_AND_HOUSE")
        return self


class CostRange(Contract):
    low_lkr: float = Field(ge=0)
    expected_lkr: float = Field(ge=0)
    high_lkr: float = Field(ge=0)

    @model_validator(mode="after")
    def ordered(self):
        if not self.low_lkr <= self.expected_lkr <= self.high_lkr:
            raise ValueError("Cost range must satisfy low <= expected <= high")
        return self


class BudgetAssessment(Contract):
    basis: Literal["SALE_TOTAL", "MONTHLY_RENT", "TOTAL_PROJECT", "CONSTRUCTION"]
    budget_lkr: float | None = Field(default=None, ge=0)
    price_lkr: float | None = Field(default=None, ge=0)
    construction: CostRange | None = None
    total_project: CostRange | None = None
    assessed_cost: CostRange | None = None
    expected_margin_lkr: float | None = None
    upstream_expected_margin_lkr: float | None = None
    upstream_status: str | None = None
    status: Literal["WITHIN_BUDGET", "POTENTIALLY_FEASIBLE", "TIGHT_BUDGET", "ABOVE_BUDGET", "UNKNOWN"] = "UNKNOWN"
    authoritative: bool = False
    not_included: list[str] = Field(default_factory=list)


class PlanningEvidence(Contract):
    plan_id: str | None = None
    constraints_satisfied: bool | None = None
    exact_site_fit_verified: bool | None = None
    layout_score: float | None = Field(default=None, ge=0, le=100)
    layout_score_breakdown: dict[str, float] = Field(default_factory=dict)
    land_size_perches: float | None = Field(default=None, gt=0)
    width_ft: float | None = Field(default=None, gt=0)
    length_ft: float | None = Field(default=None, gt=0)
    bedrooms: float | None = Field(default=None, ge=0)
    bathrooms: float | None = Field(default=None, ge=0)
    floors: float | None = Field(default=None, ge=0)
    parking_spaces: float | None = Field(default=None, ge=0)
    estimated_floor_area_sqft: float | None = Field(default=None, gt=0)
    assumptions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    disclaimer: str | None = None


class EvidenceCheck(Contract):
    criterion: str
    requirement: str
    status: Literal["SATISFIED", "VIOLATED", "UNKNOWN"]
    evidence: str


class CandidateEvidence(Contract):
    """Normalized internal snapshot; no upstream business logic is invoked."""
    property: PropertyResult
    budget: BudgetAssessment
    planning: PlanningEvidence | None = None
    upstream_combination_score: float | None = None
    warnings: list[str] = Field(default_factory=list)
    uncertainty: list[str] = Field(default_factory=list)


class EligibilityAssessment(Contract):
    eligibility: Eligibility
    checks: list[EvidenceCheck] = Field(default_factory=list)
    unmet_requirements: list[str] = Field(default_factory=list)
    uncertainty: list[str] = Field(default_factory=list)


class CriterionAssessment(Contract):
    criterion: str
    normalized_score: float = Field(ge=0, le=1)
    weight: float = Field(ge=0, le=1)
    contribution: float = Field(ge=0, le=100)
    evidence_status: Literal["KNOWN", "PARTIAL", "UNKNOWN"]
    explanation: str
    evidence_references: list[str] = Field(default_factory=list)


class RecommendationItem(Contract):
    listing_id: str
    title: str
    rank: int | None = Field(default=None, ge=1)
    final_recommendation_score: float = Field(ge=0, le=100)
    score_kind: Literal["DECISION_SUPPORT_INDEX"] = "DECISION_SUPPORT_INDEX"
    upstream_retrieval_relevance_score: float = Field(ge=0, le=1)
    upstream_retrieval_score_breakdown: dict[str, float] = Field(default_factory=dict)
    upstream_combination_score: float | None = None
    agent3_layout_score: float | None = None
    eligibility: Eligibility
    criteria: list[CriterionAssessment]
    constraint_checks: list[EvidenceCheck]
    strengths: list[str] = Field(default_factory=list)
    trade_offs: list[str] = Field(default_factory=list)
    unmet_requirements: list[str] = Field(default_factory=list)
    budget: BudgetAssessment
    planning: PlanningEvidence | None = None
    warnings: list[str] = Field(default_factory=list)
    uncertainty: list[str] = Field(default_factory=list)


class OwnedLandAssessment(Contract):
    eligibility: Eligibility
    budget: BudgetAssessment
    planning: PlanningEvidence
    constraint_checks: list[EvidenceCheck] = Field(default_factory=list)
    unmet_requirements: list[str] = Field(default_factory=list)
    uncertainty: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)


class CandidateCoverage(Contract):
    total_matching_candidates: int = Field(default=0, ge=0)
    retrieved_count: int = Field(default=0, ge=0)
    planning_assessed_count: int = Field(default=0, ge=0)
    evaluated_count: int = Field(default=0, ge=0)
    ranked_count: int = Field(default=0, ge=0)
    returned_count: int = Field(default=0, ge=0)
    excluded_ids: list[str] = Field(default_factory=list)
    unassessed_ids: list[str] = Field(default_factory=list)
    retrieval_truncated: bool = False
    planning_coverage_limited: bool = False
    scope: str = "Best among the evaluated retrieved candidates; not the entire property market."


class CandidateComparison(Contract):
    first_listing_id: str
    second_listing_id: str
    score_difference: float
    expected_cost_difference_lkr: float | None = None
    budget_basis: str


class RecommendationResponse(Contract):
    status: ResponseStatus
    policy_version: str
    recommendations: list[RecommendationItem] = Field(default_factory=list)
    alternatives: list[RecommendationItem] = Field(default_factory=list)
    comparisons: list[CandidateComparison] = Field(default_factory=list)
    owned_land_assessment: OwnedLandAssessment | None = None
    coverage: CandidateCoverage = Field(default_factory=CandidateCoverage)
    warnings: list[str] = Field(default_factory=list)
    clarification_questions: list[str] = Field(default_factory=list)
    explanation_status: Literal["DETERMINISTIC"] = "DETERMINISTIC"
