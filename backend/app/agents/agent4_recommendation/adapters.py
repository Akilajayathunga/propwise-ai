"""Read existing output contracts without calling or modifying Agents 1--3."""
from collections import Counter
from math import isclose, isfinite

from pydantic import ValidationError

from app.schemas.recommendation import (
    BudgetAssessment, CandidateEvidence, CostRange, PlanningEvidence,
    RecommendationContext,
)


def number(value, *, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if not isfinite(value) or value < 0 or (positive and value == 0):
        return None
    return float(value)


def signed_number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        return None
    return float(value)


def cost_range(value):
    if not isinstance(value, dict):
        return None
    fields = {key: number(value.get(key)) for key in ("low_lkr", "expected_lkr", "high_lkr")}
    if any(v is None for v in fields.values()):
        return None
    try:
        return CostRange(**fields)
    except ValidationError:
        return None


def text_list(value):
    return [s for s in value if isinstance(s, str)] if isinstance(value, list) else []


def classify_budget(budget: BudgetAssessment) -> BudgetAssessment:
    """Calculate against the original budget; unknown is never affordable."""
    cap = budget.budget_lkr
    estimate = budget.assessed_cost
    if not budget.authoritative or cap is None or estimate is None:
        return budget
    budget.expected_margin_lkr = cap - estimate.expected_lkr
    if estimate.high_lkr <= cap:
        budget.status = "WITHIN_BUDGET"
    elif estimate.expected_lkr <= cap:
        budget.status = "POTENTIALLY_FEASIBLE"
    elif estimate.low_lkr <= cap:
        budget.status = "TIGHT_BUDGET"
    else:
        budget.status = "ABOVE_BUDGET"
    return budget


def property_budget(prop, req):
    renting = req.intent == "RENT_PROPERTY" or req.listing_type == "rent"
    basis = "MONTHLY_RENT" if renting else "SALE_TOTAL"
    # Deliberately never fall back to price_lkr: its unit can be ambiguous.
    price = number(prop.rent_monthly_lkr if renting else prop.sale_total_price_lkr, positive=True)
    if prop.listing_type.lower() != ("rent" if renting else "sale"):
        price = None
    cap = req.maximum_budget_lkr
    if req.intent == "BUY_LAND" and req.maximum_land_budget_lkr is not None:
        cap = req.maximum_land_budget_lkr
    estimate = CostRange(low_lkr=price, expected_lkr=price, high_lkr=price) if price is not None else None
    return classify_budget(BudgetAssessment(
        basis=basis, budget_lkr=number(cap), price_lkr=price,
        assessed_cost=estimate, authoritative=estimate is not None,
    ))


def planning_evidence(data, *, assumptions=(), warnings=(), land_size=None):
    score = number(data.get("layout_score"))
    return PlanningEvidence(
        plan_id=data.get("plan_id") if isinstance(data.get("plan_id"), str) else None,
        constraints_satisfied=data.get("constraints_satisfied") if type(data.get("constraints_satisfied")) is bool else None,
        exact_site_fit_verified=data.get("exact_site_fit_verified") if type(data.get("exact_site_fit_verified")) is bool else None,
        layout_score=score if score is not None and score <= 100 else None,
        land_size_perches=number(land_size, positive=True),
        assumptions=list(assumptions), warnings=list(warnings),
    )


def combined_evidence(prop, option, req):
    data = option.budget
    construction = cost_range(data.get("construction_estimate"))
    total = cost_range(data.get("total_project_estimate"))
    warnings = list(option.warnings)
    valid = construction is not None and total is not None
    price = number(prop.sale_total_price_lkr, positive=True)
    if price is None or prop.listing_type.lower() != "sale":
        valid = False
        warnings.append("Total-sale land price is unavailable; combined affordability is unverified.")
    if construction and total and price is not None:
        for key in ("low_lkr", "expected_lkr", "high_lkr"):
            if not isclose(getattr(total, key), price + getattr(construction, key), abs_tol=1, rel_tol=1e-9):
                valid = False
                warnings.append("Agent 3 project totals conflict with Agent 2 land price and construction estimates.")
                break
    for field in ("land_price_lkr",):
        for source in (option.property, data):
            if source.get(field) is not None and (number(source[field]) is None or price is None or not isclose(source[field], price, abs_tol=1)):
                valid = False
                warnings.append("Conflicting land prices across upstream responses.")
    # Duplicate flattened range values must agree with their canonical range.
    for prefix, estimate in (("construction", construction), ("total", total)):
        for level in ("low", "expected", "high"):
            field = f"{prefix}_{level}_lkr"
            if field in data and data[field] is not None:
                flat = number(data[field])
                if estimate is None or flat is None or not isclose(flat, getattr(estimate, f"{level}_lkr"), abs_tol=1):
                    valid = False
                    warnings.append(f"Conflicting cost evidence: {field}.")
    if data.get("budget_status") == "COST_DATA_UNAVAILABLE":
        valid = False
        warnings.append("Agent 3 reports COST_DATA_UNAVAILABLE; affordability remains unknown.")
    budget = classify_budget(BudgetAssessment(
        basis="TOTAL_PROJECT", budget_lkr=number(req.total_project_budget_lkr),
        price_lkr=price, construction=construction, total_project=total,
        assessed_cost=total, authoritative=valid,
        upstream_status=data.get("budget_status") if isinstance(data.get("budget_status"), str) else None,
        upstream_expected_margin_lkr=signed_number(data.get("expected_margin_lkr")),
        not_included=text_list(data.get("not_included")),
    ))
    plan = planning_evidence(option.planning, assumptions=option.assumptions, warnings=option.warnings, land_size=option.property.get("land_size_perches"))
    for name in ("bedrooms", "bathrooms", "floors", "parking_spaces"):
        setattr(plan, name, number(option.house.get(name)))
    plan.estimated_floor_area_sqft = number(option.house.get("estimated_floor_area_sqft"), positive=True)
    plan.disclaimer = option.cost_disclaimer
    # The combined API does not return dimensions. A true upstream flag alone
    # does not manufacture width/length evidence in this adapter.
    return CandidateEvidence(property=prop.model_copy(deep=True), budget=budget, planning=plan,
        upstream_combination_score=signed_number(option.combination_score), warnings=warnings)


def adapt_candidates(context: RecommendationContext):
    """Return normalized candidates, excluded IDs and warnings; duplicate IDs fail closed."""
    search = context.property_search
    if search is None:
        return [], [], ["Agent 2 results are unavailable."]
    counts = Counter(p.listing_id for p in search.results)
    excluded = {key for key, count in counts.items() if count != 1 or not key.strip() or key != key.strip()}
    warnings = list(search.warnings)
    if excluded:
        warnings.append("Blank, noncanonical or duplicate Agent 2 listing IDs were excluded.")
    properties = {p.listing_id: p for p in search.results if p.listing_id not in excluded}
    options = {}
    if context.land_house is not None:
        warnings.extend(context.land_house.warnings)
        option_counts = Counter(str(o.property.get("listing_id", "")) for o in context.land_house.options)
        for option in context.land_house.options:
            key = option.property.get("listing_id")
            if not isinstance(key, str) or key not in properties:
                warnings.append("Agent 3 option with an unknown listing ID was excluded.")
                if isinstance(key, str):
                    excluded.add(key)
                continue
            identities = [option.property.get("full_ad", {}).get("listing_id") if isinstance(option.property.get("full_ad"), dict) else None,
                          option.technical_data.get("listing_id")]
            source = option.technical_data.get("source_property")
            if isinstance(source, dict):
                identities.append(source.get("listing_id"))
            if option_counts[key] != 1 or any(identity is not None and identity != key for identity in identities):
                excluded.add(key)
                warnings.append(f"Conflicting or duplicate Agent 3 identity for {key}; candidate excluded.")
                continue
            options[key] = option
    candidates = []
    for key, prop in sorted(properties.items()):
        if key in excluded:
            continue
        if context.requirements.intent == "LAND_AND_HOUSE":
            if key in options:
                candidate = combined_evidence(prop, options[key], context.requirements)
            else:
                candidate = CandidateEvidence(property=prop.model_copy(deep=True), budget=BudgetAssessment(
                    basis="TOTAL_PROJECT", budget_lkr=number(context.requirements.total_project_budget_lkr),
                    price_lkr=number(prop.sale_total_price_lkr, positive=True)),
                    uncertainty=["Agent 3 has not assessed this retrieved candidate."])
        else:
            candidate = CandidateEvidence(property=prop.model_copy(deep=True), budget=property_budget(prop, context.requirements))
        if search.relaxed_filters:
            candidate.warnings.append("Agent 2 relaxed its filters; Agent 4 checks the original requirements.")
        candidates.append(candidate)
    return candidates, sorted(excluded), sorted(set(warnings))


def adapt_owned_land(context: RecommendationContext):
    response = context.owned_land
    if response is None:
        return None
    req = context.requirements
    construction = cost_range(response.construction_cost_estimate)
    total = cost_range(response.total_project_estimate)
    # Owned land uses construction affordability, without charging for land again.
    caps = [cap for cap in (req.construction_budget_lkr, req.total_project_budget_lkr) if cap is not None]
    cap = min(caps) if caps else None
    budget = classify_budget(BudgetAssessment(
        basis="CONSTRUCTION", budget_lkr=number(cap), construction=construction,
        total_project=total, assessed_cost=construction,
        authoritative=response.budget_estimation_available and construction is not None and response.budget_status != "COST_DATA_UNAVAILABLE",
        upstream_status=response.budget_status,
    ))
    site = (response.plan or {}).get("site", {})
    site = site if isinstance(site, dict) else {}
    selected = response.selected_property
    plan = planning_evidence(response.model_dump(), assumptions=response.assumptions,
        warnings=response.warnings, land_size=site.get("land_size_perches", selected.land_size_perches if selected else None))
    plan.width_ft = number(site.get("width_ft", selected.land_width_ft if selected else None), positive=True)
    plan.length_ft = number(site.get("length_ft", selected.land_length_ft if selected else None), positive=True)
    plan.layout_score_breakdown = {k: v for k, v in response.score_breakdown.items() if signed_number(v) is not None}
    plan.estimated_floor_area_sqft = number(response.estimated_floor_area_sqft, positive=True)
    plan.suggestions = list(response.suggestions)
    plan.disclaimer = response.disclaimer
    raw = response.plan or {}
    rooms = raw.get("rooms")
    if isinstance(rooms, list):
        types = [r.get("type", "") for r in rooms if isinstance(r, dict)]
        plan.bedrooms = sum(t in {"bedroom", "master_bedroom"} for t in types)
        plan.bathrooms = sum(t in {"bathroom", "master_bathroom"} for t in types)
    if isinstance(raw.get("floors"), list):
        plan.floors = len(raw["floors"])
    return budget, plan
