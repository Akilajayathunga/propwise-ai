"""Phase 1 contract and behavioral tests; no upstream agents or I/O invoked."""
from itertools import permutations

import pytest
from pydantic import ValidationError

from app.agents.agent4_recommendation.agent import RecommendationAgent
from app.agents.agent4_recommendation.policy import RankingPolicy, Weights
from app.schemas.planning import LandHouseEvaluationResponse, LandHouseOption, PlanningResponse
from app.schemas.property import Agent2Result, PropertyResult
from app.schemas.recommendation import (
    Eligibility, RecommendationContext, RecommendationResponse, ResponseStatus,
)
from app.schemas.requirements import ParsedRequirements


def requirements(**changes):
    return ParsedRequirements(**dict({"original_query": "original request", "intent": "BUY_PROPERTY",
        "listing_type": "sale", "property_type": "house", "location": "Kandy",
        "maximum_budget_lkr": 100, "bedrooms": 3}, **changes))


def property_result(key="a", **changes):
    return PropertyResult(**dict({"listing_id": key, "title": f"Listing {key}",
        "listing_type": "sale", "property_type": "house", "location": "Kandy",
        "sale_total_price_lkr": 80, "bedrooms": 3, "bathrooms": 2,
        "land_size_perches": 10, "house_size_sqft": 1200, "score": .5}, **changes))


def search(props, **changes):
    return Agent2Result(**dict({"results": props, "returned": len(props), "total_found": len(props)}, **changes))


def recommend(props, req=None, *, upstream=None, combined=None, policy=None, top_k=3):
    context = RecommendationContext(requirements=req or requirements(),
        property_search=upstream or search(props), land_house=combined, top_k=top_k)
    return RecommendationAgent(policy or RankingPolicy()).recommend(context)


def land_req(**changes):
    return requirements(**dict({"intent": "LAND_AND_HOUSE", "property_type": "land",
        "maximum_budget_lkr": None, "total_project_budget_lkr": 100,
        "land_size_perches": 8}, **changes))


def land(key="a", **changes):
    return property_result(key, **dict({"property_type": "land", "sale_total_price_lkr": 20,
                                     "bedrooms": None, "bathrooms": None}, **changes))


def option(prop, *, low=40, expected=50, high=60, constraints=True, exact=False, score=80, status="WITHIN_BUDGET", combination=75):
    price = prop.sale_total_price_lkr or 0
    return LandHouseOption(option_id=f"option-{prop.listing_id}",
        property={"listing_id": prop.listing_id, "land_price_lkr": price,
                  "land_size_perches": prop.land_size_perches, "full_ad": prop.model_dump()},
        house={"bedrooms": 3, "bathrooms": 2, "floors": 1, "parking_spaces": 1, "estimated_floor_area_sqft": 1200},
        budget={"construction_estimate": {"low_lkr": low, "expected_lkr": expected, "high_lkr": high},
                "total_project_estimate": {"low_lkr": low + price, "expected_lkr": expected + price, "high_lkr": high + price},
                "budget_status": status, "expected_margin_lkr": 100 - price - expected,
                "not_included": ["Professional fees"]},
        planning={"plan_id": f"plan-{prop.listing_id}", "constraints_satisfied": constraints,
                  "exact_site_fit_verified": exact, "layout_score": score},
        combination_score=combination, assumptions=["Conceptual costs"], warnings=["Site inspection required"])


def combined(*options):
    return LandHouseEvaluationResponse(options=list(options), returned=len(options), budget_estimation_available=True)


def all_items(result):
    return {item.listing_id: item for item in result.recommendations + result.alternatives}


def test_reorders_agent2_candidates_independently():
    result = recommend([property_result("expensive", sale_total_price_lkr=99, score=.99),
                        property_result("affordable", sale_total_price_lkr=60, score=.1)])
    assert [x.listing_id for x in result.recommendations] == ["affordable", "expensive"]
    assert result.recommendations[0].upstream_retrieval_relevance_score == .1


def test_candidate_permutations_produce_identical_responses():
    props = [property_result("b"), property_result("a"), property_result("c", sale_total_price_lkr=101)]
    outputs = [recommend(list(order)).model_dump() for order in permutations(props)]
    assert all(result == outputs[0] for result in outputs)


def test_hard_budget_violation_cannot_win_with_other_factors():
    result = recommend([property_result("violation", sale_total_price_lkr=101, score=1, is_verified=True, features="pool"),
                        property_result("safe", sale_total_price_lkr=90, score=0)])
    assert result.recommendations[0].listing_id == "safe"
    rejected = all_items(result)["violation"]
    assert rejected.eligibility == Eligibility.HARD_CONSTRAINT_VIOLATION
    assert rejected.budget.status == "ABOVE_BUDGET"
    assert rejected.rank is None


def test_relaxed_results_preserve_original_constraint_violation():
    prop = property_result(sale_total_price_lkr=115)
    result = recommend([prop], upstream=search([prop], relaxed_filters=True, filters_applied={"max_budget_lkr": 120}))
    assert result.status == ResponseStatus.NO_SUITABLE_OPTION
    assert result.alternatives[0].budget.budget_lkr == 100
    assert any("relaxed" in warning for warning in result.alternatives[0].warnings)


@pytest.mark.parametrize("price", [None, 0, -1, float("nan"), float("inf")])
def test_missing_or_invalid_prices_are_unknown(price):
    result = recommend([property_result(sale_total_price_lkr=price)])
    assert result.status == ResponseStatus.INSUFFICIENT_EVIDENCE
    assert result.alternatives[0].budget.status == "UNKNOWN"
    assert result.alternatives[0].eligibility == Eligibility.INSUFFICIENT_EVIDENCE


def test_ambiguous_generic_price_does_not_establish_affordability():
    item = recommend([property_result(sale_total_price_lkr=None, price_lkr=10, price_basis="per_perch")]).alternatives[0]
    assert item.budget.price_lkr is None
    assert not item.budget.authoritative


def test_rent_uses_monthly_rent_and_not_sale_price():
    req = requirements(intent="RENT_PROPERTY", listing_type="rent")
    result = recommend([property_result("a", listing_type="rent", rent_monthly_lkr=80, sale_total_price_lkr=9999),
                        property_result("b", listing_type="rent", rent_monthly_lkr=120, sale_total_price_lkr=1)], req)
    assert result.recommendations[0].listing_id == "a"
    assert result.recommendations[0].budget.basis == "MONTHLY_RENT"
    assert all_items(result)["b"].budget.status == "ABOVE_BUDGET"


def test_purchase_does_not_use_monthly_rent_as_sale_price():
    assert recommend([property_result(sale_total_price_lkr=None, rent_monthly_lkr=1)]).status == ResponseStatus.INSUFFICIENT_EVIDENCE


def test_land_purchase_uses_land_budget_and_size_without_house_bedrooms():
    req = requirements(intent="BUY_LAND", property_type="land", maximum_land_budget_lkr=50, land_size_perches=8)
    result = recommend([land()], req)
    assert result.recommendations[0].budget.budget_lkr == 50
    assert not any("bedrooms" in c.requirement for c in result.recommendations[0].constraint_checks)


def test_land_house_checks_total_project_not_just_land_cost():
    a, b = land("a"), land("b")
    result = recommend([a, b], land_req(), combined=combined(option(a, expected=90, high=100), option(b)))
    assert result.recommendations[0].listing_id == "b"
    item = all_items(result)["a"]
    assert item.budget.assessed_cost.expected_lkr == 110
    assert item.eligibility == Eligibility.HARD_CONSTRAINT_VIOLATION
    assert item.budget.expected_margin_lkr == -10


def test_failed_layout_is_not_recommended_despite_high_composites():
    a, b = land("a", score=1), land("b", score=.1)
    result = recommend([a, b], land_req(), combined=combined(option(a, constraints=False, combination=100), option(b, combination=1)))
    assert result.recommendations[0].listing_id == "b"
    failed = all_items(result)["a"]
    assert failed.eligibility == Eligibility.HARD_CONSTRAINT_VIOLATION
    assert any("does not prove" in text for text in failed.trade_offs)
    assert next(c for c in failed.criteria if c.criterion == "planning").contribution == 0


def test_cost_data_unavailable_is_not_affordable_even_with_numeric_estimates():
    prop = land()
    result = recommend([prop], land_req(), combined=combined(option(prop, status="COST_DATA_UNAVAILABLE")))
    assert result.status == ResponseStatus.INSUFFICIENT_EVIDENCE
    assert result.alternatives[0].budget.status == "UNKNOWN"


@pytest.mark.parametrize("exact", [False, True])
def test_combined_missing_site_dimensions_remain_uncertain(exact):
    prop = land()
    item = recommend([prop], land_req(), combined=combined(option(prop, exact=exact))).recommendations[0]
    assert item.eligibility == Eligibility.CONDITIONAL
    assert item.planning.width_ft is None
    assert any("Site dimensions" in text for text in item.uncertainty)
    assert item.planning.assumptions == ["Conceptual costs"]
    assert "Site inspection required" in item.warnings


def test_ties_use_retrieval_then_listing_id_deterministically():
    result = recommend([property_result("z", score=.8), property_result("b", score=.9), property_result("a", score=.9)])
    assert [x.listing_id for x in result.recommendations] == ["a", "b", "z"]
    no_retrieval = recommend([property_result("a", score=0), property_result("b", score=1)], policy=RankingPolicy(use_retrieval_tiebreak=False))
    assert no_retrieval.recommendations[0].listing_id == "a"


def test_unknown_agent3_listing_ids_never_enter_recommendations():
    prop, foreign = land("a"), land("foreign")
    result = recommend([prop], land_req(), combined=combined(option(foreign)))
    assert "foreign" not in all_items(result)
    assert "foreign" in result.coverage.excluded_ids
    assert result.coverage.unassessed_ids == ["a"]


def test_conflicting_nested_listing_id_is_excluded():
    prop = land()
    opt = option(prop)
    opt.property["full_ad"]["listing_id"] = "forged"
    result = recommend([prop], land_req(), combined=combined(opt))
    assert result.status == ResponseStatus.INSUFFICIENT_EVIDENCE
    assert not all_items(result)


def test_duplicate_agent2_or_agent3_ids_are_excluded():
    prop = land()
    assert not all_items(recommend([prop, prop], land_req()))
    assert not all_items(recommend([prop], land_req(), combined=combined(option(prop), option(prop))))


def test_no_candidates_and_all_violations_report_no_suitable_option():
    assert recommend([]).status == ResponseStatus.NO_SUITABLE_OPTION
    assert recommend([property_result(bedrooms=1)]).status == ResponseStatus.NO_SUITABLE_OPTION


def test_composite_scores_do_not_change_agent4_numeric_score():
    prop = land()
    baseline = recommend([prop], land_req(), combined=combined(option(prop, combination=1))).recommendations[0]
    changed = prop.model_copy(update={"score": .99, "score_breakdown": {"budget_fit": .35}})
    after = recommend([changed], land_req(), combined=combined(option(changed, combination=99))).recommendations[0]
    assert baseline.final_recommendation_score == after.final_recommendation_score
    assert baseline.criteria == after.criteria
    assert after.upstream_combination_score == 99
    assert after.agent3_layout_score == 80
    assert after.score_kind == "DECISION_SUPPORT_INDEX"


def test_coverage_discloses_retrieval_and_planning_limits():
    props = [land("a"), land("b")]
    result = recommend(props, land_req(), upstream=search(props, total_found=100), combined=combined(option(props[0])))
    assert result.coverage.retrieval_truncated
    assert result.coverage.planning_coverage_limited
    assert result.coverage.planning_assessed_count == 1
    assert result.coverage.unassessed_ids == ["b"]
    assert "not the entire property market" in result.coverage.scope


@pytest.mark.parametrize("field,value", [("total_project_estimate", {"low_lkr": 1, "expected_lkr": 2, "high_lkr": 3}),
                                          ("construction_high_lkr", 1)])
def test_conflicting_cost_evidence_cannot_establish_affordability(field, value):
    prop = land()
    opt = option(prop)
    opt.budget[field] = value
    assert recommend([prop], land_req(), combined=combined(opt)).status == ResponseStatus.INSUFFICIENT_EVIDENCE


def test_unknown_room_evidence_is_not_satisfied():
    item = recommend([property_result(bedrooms=None)]).recommendations[0]
    assert item.eligibility == Eligibility.CONDITIONAL
    assert any(c.status == "UNKNOWN" and "bedrooms" in c.requirement for c in item.constraint_checks)


def test_unproven_and_negated_preferences_get_no_credit():
    req = requirements(preferences=["pool"])
    a = recommend([property_result(features="no pool")], req).recommendations[0]
    b = recommend([property_result(features="pool")], req).recommendations[0]
    assert next(c for c in a.criteria if c.criterion == "preferences").normalized_score == 0
    assert b.final_recommendation_score > a.final_recommendation_score


def test_location_and_size_hard_constraints_are_rechecked():
    req = requirements(minimum_house_size_sqft=1000)
    result = recommend([property_result("wrong-location", location="Galle"), property_result("small", house_size_sqft=900)], req)
    assert result.status == ResponseStatus.NO_SUITABLE_OPTION


def test_policy_is_validated_immutable_and_versioned():
    policy = RankingPolicy()
    assert policy.land_house_weights.model_dump() == dict(budget=.35, location=.20, requirements=0, size=.15, planning=.15, preferences=.05, evidence_quality=.10)
    with pytest.raises(ValidationError):
        Weights(budget=1, location=1, preferences=0, evidence_quality=0)
    with pytest.raises(ValidationError):
        policy.land_house_weights.budget = .1
    custom = RankingPolicy(version="experiment-2", property_weights=Weights(budget=1, location=0, preferences=0, evidence_quality=0))
    result = recommend([property_result()], policy=custom)
    assert result.policy_version == "experiment-2"


def owned_response(**changes):
    return PlanningResponse(**dict({"plan_id": "owned", "constraints_satisfied": True, "exact_site_fit_verified": False,
        "layout_score": 85, "budget_estimation_available": True, "budget_status": "WITHIN_BUDGET",
        "construction_cost_estimate": {"low_lkr": 40, "expected_lkr": 50, "high_lkr": 60},
        "assumptions": ["Fees excluded"], "warnings": ["Conceptual envelope"], "disclaimer": "Conceptual only",
        "plan": {"site": {"land_size_perches": 10}, "rooms": [{"type": "master_bedroom"}, {"type": "bedroom"}, {"type": "bedroom"}]}}, **changes))


def test_owned_land_returns_assessment_without_property_ranking():
    context = RecommendationContext(requirements=requirements(intent="PLAN_HOUSE", construction_budget_lkr=100), owned_land=owned_response())
    result = RecommendationAgent().recommend(context)
    assert result.status == ResponseStatus.OK
    assert not result.recommendations
    assert result.owned_land_assessment.budget.basis == "CONSTRUCTION"
    assert result.owned_land_assessment.eligibility == Eligibility.CONDITIONAL
    assert result.owned_land_assessment.planning.assumptions == ["Fees excluded"]
    assert result.owned_land_assessment.next_steps


def test_owned_land_failed_plan_and_missing_costs_are_not_success():
    req = requirements(intent="PLAN_HOUSE", construction_budget_lkr=100)
    failed = RecommendationAgent().recommend(RecommendationContext(requirements=req, owned_land=owned_response(constraints_satisfied=False)))
    assert failed.status == ResponseStatus.NO_SUITABLE_OPTION
    missing = RecommendationAgent().recommend(RecommendationContext(requirements=req, owned_land=owned_response(budget_status="COST_DATA_UNAVAILABLE")))
    assert missing.status == ResponseStatus.INSUFFICIENT_EVIDENCE


def test_context_rejects_cross_workflow_evidence():
    with pytest.raises(ValidationError):
        RecommendationContext(requirements=requirements(), owned_land=owned_response())


def test_missing_or_conflicting_requirements_need_clarification():
    assert recommend([property_result()], requirements(maximum_budget_lkr=None)).status == ResponseStatus.NEEDS_CLARIFICATION
    assert recommend([property_result()], requirements(listing_type="rent")).status == ResponseStatus.NEEDS_CLARIFICATION


def test_response_round_trip_and_no_input_mutation():
    prop = land()
    context = RecommendationContext(requirements=land_req(), property_search=search([prop]), land_house=combined(option(prop)))
    before = context.model_dump_json()
    response = RecommendationAgent().recommend(context)
    assert context.model_dump_json() == before
    assert RecommendationResponse.model_validate_json(response.model_dump_json()) == response


def test_comparisons_use_matching_cost_basis_and_correct_difference():
    result = recommend([property_result("a", sale_total_price_lkr=60), property_result("b", sale_total_price_lkr=80)])
    assert result.comparisons[0].expected_cost_difference_lkr == -20
    assert result.comparisons[0].budget_basis == "SALE_TOTAL"


def test_original_construction_sub_budget_is_not_lost_in_total_budget():
    prop = land()
    result = recommend([prop], land_req(construction_budget_lkr=45), combined=combined(option(prop)))
    assert result.status == ResponseStatus.NO_SUITABLE_OPTION
    assert "Construction estimate fits original construction budget" in result.alternatives[0].unmet_requirements


def test_explicit_zero_parking_and_floor_count_are_rechecked():
    prop = land()
    result = recommend([prop], land_req(parking_spaces=0, floors=2), combined=combined(option(prop)))
    assert result.status == ResponseStatus.NO_SUITABLE_OPTION
    assert "parking_spaces equals 0" in result.alternatives[0].unmet_requirements
    assert "floors equals 2" in result.alternatives[0].unmet_requirements


def test_land_advertisement_cannot_prove_future_house_preferences():
    prop = land(features="office, premium")
    item = recommend([prop], land_req(office_required=True, finish_level="premium"), combined=combined(option(prop))).recommendations[0]
    assert all(c.status == "UNKNOWN" for c in item.constraint_checks if c.criterion == "preferences")


def test_owned_land_honors_both_construction_and_total_budget_limits():
    req = requirements(intent="PLAN_HOUSE", construction_budget_lkr=100, total_project_budget_lkr=45)
    result = RecommendationAgent().recommend(RecommendationContext(requirements=req, owned_land=owned_response()))
    assert result.status == ResponseStatus.NO_SUITABLE_OPTION
    assert result.owned_land_assessment.budget.budget_lkr == 45


def test_missing_upstream_responses_are_insufficient_evidence():
    assert RecommendationAgent().recommend(RecommendationContext(requirements=requirements())).status == ResponseStatus.INSUFFICIENT_EVIDENCE
    assert RecommendationAgent().recommend(RecommendationContext(requirements=requirements(intent="PLAN_HOUSE", construction_budget_lkr=100))).status == ResponseStatus.INSUFFICIENT_EVIDENCE


def test_high_scenario_risk_is_conditional_and_preserved():
    prop = land()
    item = recommend([prop], land_req(), combined=combined(option(prop, high=100))).recommendations[0]
    assert item.budget.status == "POTENTIALLY_FEASIBLE"
    assert item.eligibility == Eligibility.CONDITIONAL
    assert any("high estimate" in text for text in item.trade_offs)


def test_budget_improvement_cannot_reduce_score_with_other_evidence_fixed():
    scores = [recommend([property_result(sale_total_price_lkr=price)]).recommendations[0].final_recommendation_score for price in [99, 80, 50]]
    assert scores == sorted(scores)


def test_custom_policy_can_reach_full_score_without_float_overflow():
    policy = RankingPolicy(budget_meets_ceiling_credit=1, budget_headroom_credit=0)
    item = recommend([property_result()], policy=policy).recommendations[0]
    assert item.final_recommendation_score == pytest.approx(100)
    assert sum(c.weight for c in item.criteria) == pytest.approx(1)
