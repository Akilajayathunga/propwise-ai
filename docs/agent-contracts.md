# Agent Contracts

This document summarizes the agent boundaries. Concrete Pydantic contracts now exist in `backend/app/schemas/`; the Agent 4 section below distinguishes internal evidence from public user input.

## Agent 1: Requirement & Intent Understanding

Input: natural language from the user.

Output: structured requirements describing intent, budget, location preferences, property constraints, and route selection.

## Agent 2: Property Search & Analysis

Input: structured property requirements.

Output: relevance-ranked retrieved properties with analysis signals. This is upstream retrieval ordering, not Agent 4's final decision-support ranking; Agent 2 behavior is preserved.

## Agent 3: Home Planning & Budget Estimation

Input: house or land-and-house requirements.

Input may include selected land context from Agent 2. Agent 3 adapts Agent 2 property fields into `SelectedPropertyContext`:

| Agent 2 Field | Agent 3 Field |
| --- | --- |
| `listing_id` | `listing_id` |
| `location` | `location` |
| `district` | `district` |
| `property_type` | `property_type` |
| `land_size_perches` | `land_size_perches` |
| `sale_total_price_lkr` | `land_price_lkr` |
| `score` | `source_score` |

Optional fields such as `land_width_ft`, `land_length_ft`, and `road_side` remain `null` when Agent 2 does not provide them. Agent 3 must not invent these values.

Output: conceptual canonical plan JSON, SVG floor-plan visuals, PNG previews, conceptual DXF, budget status, warnings, and responsible AI disclaimer.

Budget estimation uses `data/knowledge/construction_costs.json`. If verified construction rates are unavailable, Agent 3 returns `budget_estimation_available=false` and `budget_status=COST_DATA_UNAVAILABLE`.

## Agent 4: Recommendation & Decision Support

Internal input: `RecommendationContext` pairs confirmed requirements with the
server-obtained `Agent2Result`, `LandHouseEvaluationResponse` or `PlanningResponse`
required by the workflow. Public input is `RecommendationRequest`: requirements,
bounded `top_k`, `explanation_enabled`, and optional owned-land site inputs.
Clients cannot supply trusted candidate scores, prices, planning outcomes or rankings.

Output: `RecommendationResponse` contains deterministic `RecommendationItem`
entries, `CriterionAssessment` breakdowns, alternatives, comparisons,
`CandidateCoverage`, and/or `OwnedLandAssessment`. The public
`RecommendationAPIResponse` adds safe presentation data and clarification fields.
Decision statuses are `OK`, `NEEDS_CLARIFICATION`, `NO_SUITABLE_OPTION` and
`INSUFFICIENT_EVIDENCE`.

The response `explanation_status` is `LLM`, `DETERMINISTIC_FALLBACK`, or
`DETERMINISTIC`. When disabled, the explanation attachment is `null`; otherwise
its source records `LLM` or `DETERMINISTIC_FALLBACK`.
`ExplanationDraft` is validated before rendering; evidence references, candidate
identity, rank, score, eligibility, budget and planning echoes are checked.
Gemini synthesizes grounded prose only. Failures retain the deterministic result.
Human-readable enum formatting changes display prose, not structured enum values.

The public deterministic `top_k` allows 1-10 recommendations. The explanation-only
bound of 5 recommendations + 2 alternatives does not change that response.

Sources: `schemas/recommendation.py`, `schemas/recommendation_api.py` and
`agents/agent4_recommendation/explanation_models.py` under `backend/app/`.
See [Phase 2](agent4-phase2.md) and [Phase 3](agent4-phase3.md) for details.

Historical note: the foundation version of this document contained conceptual
interfaces only; its statement that no schemas or business logic existed no longer
applies to the implemented demo.
