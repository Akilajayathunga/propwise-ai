"""Phase 1 entry point: pure evidence-in, deterministic recommendation-out.

No I/O, artifact generation, API integration or LLM use occurs here.
"""
from math import isfinite

from app.agents.agent4_recommendation.adapters import adapt_candidates, adapt_owned_land
from app.agents.agent4_recommendation.decision_support import assess_owned_land, build_recommendation, compare_recommendations
from app.agents.agent4_recommendation.eligibility import assess_eligibility
from app.agents.agent4_recommendation.policy import DEFAULT_POLICY, RankingPolicy
from app.agents.agent4_recommendation.ranking import rank_candidates, score_candidate
from app.schemas.recommendation import (
    CandidateCoverage, Eligibility, RecommendationContext, RecommendationResponse, ResponseStatus,
)


def clarification_questions(req):
    supported = {"BUY_PROPERTY", "RENT_PROPERTY", "BUY_LAND", "LAND_AND_HOUSE", "PLAN_HOUSE", "COMPARE_PROPERTIES"}
    questions = []
    if req.intent not in supported:
        questions.append("Choose property purchase, rental, land purchase, land + house or owned-land planning.")
    if req.intent == "COMPARE_PROPERTIES" and req.listing_type is None:
        questions.append("Are the compared properties for sale or monthly rent?")
    if ((req.intent == "RENT_PROPERTY" and req.listing_type == "sale") or
        (req.intent in {"BUY_PROPERTY", "BUY_LAND", "LAND_AND_HOUSE"} and req.listing_type == "rent")):
        questions.append("Resolve the conflicting intent and listing type.")
    for name, value in req.model_dump().items():
        if isinstance(value, (int, float)) and not isinstance(value, bool) and (not isfinite(value) or value < 0):
            questions.append(f"Provide a valid nonnegative {name}.")
    for low, high in ((req.minimum_budget_lkr, req.maximum_budget_lkr),
                      (req.minimum_land_size_perches, req.maximum_land_size_perches)):
        if low is not None and high is not None and low > high:
            questions.append("Resolve the conflicting minimum and maximum requirements.")
    if req.intent == "LAND_AND_HOUSE":
        budget = req.total_project_budget_lkr
    elif req.intent == "PLAN_HOUSE":
        budget = req.construction_budget_lkr if req.construction_budget_lkr is not None else req.total_project_budget_lkr
    elif req.intent == "BUY_LAND":
        budget = req.maximum_land_budget_lkr if req.maximum_land_budget_lkr is not None else req.maximum_budget_lkr
    else:
        budget = req.maximum_budget_lkr
    if budget is None:
        questions.append("Provide the original budget ceiling for this workflow.")
    return sorted(set(questions))


def response_status(eligible, categories):
    if eligible:
        return ResponseStatus.OK
    if not categories or all(c == Eligibility.HARD_CONSTRAINT_VIOLATION for c in categories):
        return ResponseStatus.NO_SUITABLE_OPTION
    return ResponseStatus.INSUFFICIENT_EVIDENCE


class RecommendationAgent:
    def __init__(self, policy: RankingPolicy = DEFAULT_POLICY):
        self.policy = policy

    def recommend(self, context: RecommendationContext) -> RecommendationResponse:
        req = context.requirements
        questions = clarification_questions(req)
        if questions:
            search = context.property_search
            received = len(search.results) if search else 0
            total = max(received, search.total_found) if search else 0
            return RecommendationResponse(status=ResponseStatus.NEEDS_CLARIFICATION,
                policy_version=self.policy.version, clarification_questions=questions,
                warnings=list(search.warnings) if search else [],
                coverage=CandidateCoverage(total_matching_candidates=total, retrieved_count=received,
                    retrieval_truncated=total > received))
        if req.intent == "PLAN_HOUSE":
            adapted = adapt_owned_land(context)
            if adapted is None:
                return RecommendationResponse(status=ResponseStatus.INSUFFICIENT_EVIDENCE,
                    policy_version=self.policy.version, warnings=["Agent 3 planning evidence is unavailable."])
            assessment = assess_owned_land(req, *adapted)
            eligible = assessment.eligibility in {Eligibility.ELIGIBLE, Eligibility.CONDITIONAL}
            return RecommendationResponse(status=response_status(eligible, [assessment.eligibility]),
                policy_version=self.policy.version, owned_land_assessment=assessment,
                warnings=list(assessment.planning.warnings),
                coverage=CandidateCoverage(scope="Assessment of the supplied owned-land plan; no property ranking."))
        candidates, excluded, warnings = adapt_candidates(context)
        items = []
        for candidate in candidates:
            assessment = assess_eligibility(candidate, req)
            criteria = score_candidate(candidate, assessment, req, self.policy)
            items.append(build_recommendation(candidate, assessment, criteria))
        ordered = rank_candidates(items, self.policy)
        suitable = [i for i in ordered if i.eligibility in {Eligibility.ELIGIBLE, Eligibility.CONDITIONAL}]
        for rank, item in enumerate(suitable, 1):
            item.rank = rank
        recommendations = suitable[:context.top_k]
        alternatives = suitable[context.top_k:] + [i for i in ordered if i not in suitable]
        search = context.property_search
        retrieved = len(search.results) if search else 0
        total = max(retrieved, search.total_found) if search else 0
        if search and (search.returned != retrieved or search.total_found < retrieved):
            warnings.append("Upstream candidate counts are inconsistent; coverage uses the actual received list.")
        unassessed = [c.property.listing_id for c in candidates if req.intent == "LAND_AND_HOUSE" and c.planning is None]
        coverage = CandidateCoverage(total_matching_candidates=total, retrieved_count=retrieved,
            planning_assessed_count=sum(c.planning is not None for c in candidates),
            evaluated_count=len(candidates), ranked_count=len(suitable), returned_count=len(recommendations),
            excluded_ids=excluded, unassessed_ids=unassessed, retrieval_truncated=total > retrieved,
            planning_coverage_limited=bool(unassessed))
        status = response_status(bool(recommendations), [i.eligibility for i in items])
        if not items and (excluded or search is None):
            status = ResponseStatus.INSUFFICIENT_EVIDENCE
        return RecommendationResponse(status=status, policy_version=self.policy.version,
            recommendations=recommendations, alternatives=alternatives,
            comparisons=compare_recommendations(recommendations), coverage=coverage,
            warnings=sorted(set(warnings)))
