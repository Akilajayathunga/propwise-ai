"""Deterministic explanations and owned-land assessment; no provider calls."""
from app.agents.agent4_recommendation.adapters import signed_number
from app.agents.agent4_recommendation.eligibility import (
    budget_checks, check, classify_checks, minimum_check, planning_checks, preference_checks,
)
from app.schemas.recommendation import (
    CandidateComparison, OwnedLandAssessment, RecommendationItem,
)


def build_recommendation(candidate, assessment, criteria):
    prop = candidate.property
    strengths = [c.requirement for c in assessment.checks if c.status == "SATISFIED"]
    trade_offs = list(assessment.unmet_requirements)
    if candidate.budget.status in {"POTENTIALLY_FEASIBLE", "TIGHT_BUDGET"}:
        trade_offs.append("Affordability depends on the cost scenario; the high estimate exceeds budget.")
    if candidate.planning and candidate.planning.constraints_satisfied is False:
        trade_offs.append("This generated layout failed; this does not prove all designs on this land are infeasible.")
    warnings = candidate.warnings + (candidate.planning.warnings if candidate.planning else [])
    warnings.append("Listing availability and claims have not been independently verified.")
    return RecommendationItem(
        listing_id=prop.listing_id, title=prop.title,
        final_recommendation_score=min(100.0, sum(c.contribution for c in criteria)),
        upstream_retrieval_relevance_score=prop.score,
        upstream_retrieval_score_breakdown={k: v for k, v in prop.score_breakdown.items() if signed_number(v) is not None},
        upstream_combination_score=candidate.upstream_combination_score,
        agent3_layout_score=candidate.planning.layout_score if candidate.planning else None,
        eligibility=assessment.eligibility, criteria=criteria, constraint_checks=assessment.checks,
        strengths=strengths, trade_offs=trade_offs, unmet_requirements=assessment.unmet_requirements,
        budget=candidate.budget, planning=candidate.planning,
        warnings=sorted(set(warnings)), uncertainty=assessment.uncertainty,
    )


def compare_recommendations(items):
    if len(items) < 2:
        return []
    first = items[0]
    comparisons = []
    for other in items[1:]:
        a, b = first.budget, other.budget
        comparable = a.authoritative and b.authoritative and a.basis == b.basis and a.assessed_cost and b.assessed_cost
        comparisons.append(CandidateComparison(
            first_listing_id=first.listing_id, second_listing_id=other.listing_id,
            score_difference=first.final_recommendation_score - other.final_recommendation_score,
            expected_cost_difference_lkr=a.assessed_cost.expected_lkr - b.assessed_cost.expected_lkr if comparable else None,
            budget_basis=a.basis,
        ))
    return comparisons


def assess_owned_land(req, budget, plan):
    checks = budget_checks(budget) + planning_checks(req, plan)
    minimum = req.minimum_land_size_perches if req.minimum_land_size_perches is not None else req.land_size_perches
    if minimum is not None:
        checks.append(minimum_check("size", "land size (perches)", minimum, plan.land_size_perches))
    if req.maximum_land_size_perches is not None:
        checks.append(check("size", "Site fits requested maximum land size",
            None if plan.land_size_perches is None else plan.land_size_perches <= req.maximum_land_size_perches,
            "Agent 3 site area"))
    # Direct planning does not expose validated preference-fulfilment fields.
    checks.extend(preference_checks(req, None))
    assessment = classify_checks(checks, budget)
    steps = list(plan.suggestions)
    if plan.constraints_satisfied is False:
        steps.append("Ask Agent 3 to evaluate a revised room programme or another layout.")
    if plan.exact_site_fit_verified is not True or not plan.width_ft or not plan.length_ft:
        steps.append("Provide measured site dimensions and obtain professional site-fit review.")
    if budget.status == "UNKNOWN":
        steps.append("Confirm the construction budget and obtain complete cost evidence.")
    elif budget.status != "WITHIN_BUDGET":
        steps.append("Review the cost range and scope before committing to construction.")
    limitations = ["Assessment of the supplied conceptual plan only; no property ranking was performed.",
                  "Construction estimates exclude costs identified in Agent 3 assumptions; they are not quotations."]
    if plan.disclaimer:
        limitations.append(plan.disclaimer)
    return OwnedLandAssessment(eligibility=assessment.eligibility, budget=budget, planning=plan,
        constraint_checks=checks, unmet_requirements=assessment.unmet_requirements,
        uncertainty=assessment.uncertainty, limitations=limitations, next_steps=sorted(set(steps)))
