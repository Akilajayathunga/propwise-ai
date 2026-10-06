"""Phase 2 contracts, independent of ranking and provider configuration."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ExplanationModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, strict=True)


class GroundedText(ExplanationModel):
    text: str = Field(min_length=1, max_length=1200)
    evidence_refs: list[str] = Field(min_length=1, max_length=12)


class PropertyExplanation(ExplanationModel):
    listing_id: str = Field(min_length=1, max_length=200)
    rank: int | None
    final_score: float
    eligibility: Literal["ELIGIBLE", "CONDITIONAL", "HARD_CONSTRAINT_VIOLATION", "INSUFFICIENT_EVIDENCE"]
    budget_status: str
    planning_constraints_satisfied: bool | None
    reason: GroundedText
    strengths: list[GroundedText] = Field(max_length=4)
    trade_offs: list[GroundedText] = Field(max_length=4)


class ExplanationDraft(ExplanationModel):
    """Provider output only. All fields are required for structured-output APIs.

    Facts in prose use {{evidence.reference}} placeholders, rendered by Python.
    Numeric decision echoes are compared exactly, never applied to Phase 1.
    """
    recommendation_order: list[str] = Field(max_length=5)
    summary: GroundedText
    top_recommendation_reason: GroundedText | None
    properties: list[PropertyExplanation] = Field(max_length=7)
    comparison_summary: list[GroundedText] = Field(max_length=4)
    warnings: list[GroundedText] = Field(max_length=5)
    alternatives: list[GroundedText] = Field(max_length=2)
    next_steps: list[GroundedText] = Field(max_length=5)


class RenderedPropertyExplanation(ExplanationModel):
    listing_id: str
    reason: str
    strengths: list[str]
    trade_offs: list[str]
    evidence_refs: list[str]


class ExplanationAttachment(ExplanationModel):
    prompt_version: str
    source: Literal["LLM", "DETERMINISTIC_FALLBACK"]
    fallback_reason: str | None = None
    attempts: int = Field(default=0, ge=0, le=2)
    summary: str
    top_recommendation_reason: str | None = None
    properties: list[RenderedPropertyExplanation] = Field(default_factory=list)
    comparison_summary: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    alternatives: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    explained_listing_ids: list[str] = Field(default_factory=list)
    explanation_scope: str = "Bounded shortlist explanation; the complete deterministic result remains authoritative."
