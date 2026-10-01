"""Independent weighted utility, with eligibility ordered before utility."""
from app.schemas.recommendation import CriterionAssessment, Eligibility


ELIGIBILITY_ORDER = {Eligibility.ELIGIBLE: 0, Eligibility.CONDITIONAL: 1,
                     Eligibility.INSUFFICIENT_EVIDENCE: 2, Eligibility.HARD_CONSTRAINT_VIOLATION: 3}


def score_candidate(candidate, assessment, req, policy):
    weights = (policy.land_house_weights if req.intent == "LAND_AND_HOUSE" else
               policy.land_weights if req.intent == "BUY_LAND" else policy.property_weights).model_dump()
    groups = {name: [c for c in assessment.checks if c.criterion == name] for name in weights}
    active = {name: weight for name, weight in weights.items() if weight > 0 and (groups[name] or name == "evidence_quality")}
    denominator = sum(active.values())
    criteria = []
    for name, weight in active.items():
        checks = groups[name]
        known = sum(c.status != "UNKNOWN" for c in checks)
        score = sum(c.status == "SATISFIED" for c in checks) / len(checks) if checks else 0
        status = "UNKNOWN" if not known else "KNOWN" if known == len(checks) else "PARTIAL"
        explanation = "; ".join(f"{c.requirement}: {c.status.lower()}" for c in checks)
        if name == "budget":
            budget = candidate.budget
            if budget.authoritative and budget.budget_lkr is not None and budget.assessed_cost is not None:
                price = budget.assessed_cost.expected_lkr
                cap = budget.budget_lkr
                if price <= cap:
                    headroom = max(0, min(1, (cap - price) / cap)) if cap > 0 else 0
                    score = policy.budget_meets_ceiling_credit + policy.budget_headroom_credit * headroom
                else:
                    score = 0
                # Other requested budget constraints must not earn false credit.
                if any(c.status == "VIOLATED" for c in checks):
                    score = 0
            else:
                score = 0
            explanation += "; original-ceiling fit plus bounded expected-cost headroom"
        elif name == "planning":
            plan = candidate.planning
            score = plan.layout_score / 100 if plan and plan.constraints_satisfied is True and plan.layout_score is not None else 0
            if plan is None or plan.layout_score is None:
                status = "UNKNOWN"
            explanation += "; layout quality credited only when generated constraints passed"
        elif name == "evidence_quality":
            all_checks = assessment.checks
            score = sum(c.status != "UNKNOWN" for c in all_checks) / len(all_checks) if all_checks else 0
            status = "KNOWN"
            explanation = "Fraction of applicable checks with known evidence; not confidence in listing truth."
        normalized_weight = weight / denominator
        criteria.append(CriterionAssessment(criterion=name, normalized_score=score,
            weight=normalized_weight, contribution=100 * normalized_weight * score,
            evidence_status=status, explanation=explanation,
            evidence_references=[f"{candidate.property.listing_id}:{c.criterion}:{c.requirement}" for c in checks]))
    return criteria


def rank_candidates(items, policy):
    # Use unrounded scores; listing ID is the final deterministic tie-break.
    return sorted(items, key=lambda item: (
        ELIGIBILITY_ORDER[item.eligibility], -item.final_recommendation_score,
        -item.upstream_retrieval_relevance_score if policy.use_retrieval_tiebreak else 0,
        item.listing_id,
    ))
