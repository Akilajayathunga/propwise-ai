"""Versioned prototype policies. Replace via RecommendationAgent(policy=...).

No upstream composite score is a weighted criterion. Missing evidence earns no
credit; request-inapplicable criteria are removed for every candidate equally.
"""
from pydantic import Field, model_validator

from app.schemas.recommendation import Contract


class Weights(Contract):
    model_config = {"frozen": True}
    budget: float = Field(ge=0, le=1)
    location: float = Field(ge=0, le=1)
    requirements: float = Field(default=0, ge=0, le=1)
    size: float = Field(default=0, ge=0, le=1)
    planning: float = Field(default=0, ge=0, le=1)
    preferences: float = Field(ge=0, le=1)
    evidence_quality: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def sum_to_one(self):
        if abs(sum(self.model_dump().values()) - 1) > 1e-9:
            raise ValueError("Criterion weights must sum to one")
        return self


class RankingPolicy(Contract):
    model_config = {"frozen": True}
    version: str = "agent4-prototype-v1"
    property_weights: Weights = Weights(budget=.25, location=.20, requirements=.20, size=.15, preferences=.10, evidence_quality=.10)
    land_weights: Weights = Weights(budget=.30, location=.25, size=.25, preferences=.10, evidence_quality=.10)
    land_house_weights: Weights = Weights(budget=.35, location=.20, size=.15, planning=.15, preferences=.05, evidence_quality=.10)
    budget_meets_ceiling_credit: float = Field(default=.70, ge=0, le=1)
    budget_headroom_credit: float = Field(default=.30, ge=0, le=1)
    use_retrieval_tiebreak: bool = True

    @model_validator(mode="after")
    def budget_credit(self):
        if abs(self.budget_meets_ceiling_credit + self.budget_headroom_credit - 1) > 1e-9:
            raise ValueError("Budget credits must sum to one")
        return self


DEFAULT_POLICY = RankingPolicy()
