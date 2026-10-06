"""Original hard constraints take precedence over every weighted score."""
import re

from app.agents.agent4_recommendation.adapters import number
from app.schemas.recommendation import Eligibility, EligibilityAssessment, EvidenceCheck


PROPERTY_TYPES = {
    "house": {"house", "villa", "bungalow"},
    "apartment": {"apartment", "flat", "condo", "holiday_rental"},
    "land": {"land", "plot"}, "commercial": {"commercial", "warehouse", "office"},
    "room_annex": {"room_annex", "room", "annex"}, "other": {"other"},
}


def check(criterion, requirement, satisfied, evidence):
    return EvidenceCheck(criterion=criterion, requirement=requirement,
        status="UNKNOWN" if satisfied is None else "SATISFIED" if satisfied else "VIOLATED",
        evidence=evidence)


def minimum_check(criterion, name, requested, actual):
    actual = number(actual)
    return check(criterion, f"{name} at least {requested}", None if actual is None else actual >= requested,
        f"{name}: {actual if actual is not None else 'unknown'}")


def preference_checks(req, features):
    # Only exact positive structured feature tokens earn credit. Free-form ads
    # are not interpreted as factual evidence and negated phrases do not match.
    tokens = {s.strip().casefold() for s in re.split(r"[,;|\n]", features or "") if s.strip()}
    preferences = list(req.preferences)
    if req.preferred_style:
        preferences.append(req.preferred_style)
    if req.finish_level:
        preferences.append(req.finish_level)
    for field, label in (("office_required", "office"), ("balcony_required", "balcony"),
                         ("family_lounge_required", "family lounge"), ("utility_room_required", "utility room")):
        if getattr(req, field) is True:
            preferences.append(label)
    return [check("preferences", pref, True if pref.strip().casefold() in tokens else None,
                  "Positive listing feature token" if pref.strip().casefold() in tokens else "No explicit supporting feature evidence")
            for pref in sorted(set(preferences)) if pref.strip()]


def planning_checks(req, plan):
    checks = [check("planning", "Generated layout satisfies Agent 3 constraints",
                    plan.constraints_satisfied if plan else None, "Agent 3 constraint result")]
    if plan:
        for name in ("bedrooms", "bathrooms", "floors", "parking_spaces"):
            requested = getattr(req, name)
            if requested is not None:
                actual = getattr(plan, name)
                if name == "floors" or (name == "parking_spaces" and requested == 0):
                    checks.append(check("requirements", f"{name} equals {requested}",
                        None if actual is None else actual == requested, f"Agent 3 {name}: {actual}"))
                else:
                    checks.append(minimum_check("requirements", name, requested, actual))
        if req.minimum_house_size_sqft is not None:
            checks.append(minimum_check("size", "conceptual floor area (sq ft)", req.minimum_house_size_sqft, plan.estimated_floor_area_sqft))
        checks.append(check("planning", "Site dimensions and fit are evidenced",
            True if plan.exact_site_fit_verified is True and plan.width_ft and plan.length_ft else None,
            "Conceptual site-fit flag and dimensions; not professional approval"))
    return checks


def budget_checks(budget):
    checks = []
    if budget.budget_lkr is None:
        checks.append(check("budget", "Budget ceiling supplied", None, "Original budget unavailable"))
    if not budget.authoritative or budget.assessed_cost is None:
        checks.append(check("budget", "Authoritative affordability evidence", None, "Price/cost basis unavailable or inconsistent"))
    elif budget.budget_lkr is not None:
        # Expected project cost must fit the original ceiling. A low-cost scenario
        # alone is not enough to recommend a project exceeding that ceiling.
        checks.append(check("budget", "Expected cost fits original budget",
            budget.assessed_cost.expected_lkr <= budget.budget_lkr,
            f"Expected {budget.assessed_cost.expected_lkr:g} LKR; ceiling {budget.budget_lkr:g} LKR ({budget.basis})"))
    return checks


def classify_checks(checks, budget, *, uncertainty=()):
    unmet = [c.requirement for c in checks if c.status == "VIOLATED"]
    unknown = [c.requirement for c in checks if c.status == "UNKNOWN"]
    unknown.extend(uncertainty)
    if budget.status in {"POTENTIALLY_FEASIBLE", "TIGHT_BUDGET"}:
        unknown.append("High construction/project cost scenario exceeds the original budget.")
    if unmet:
        category = Eligibility.HARD_CONSTRAINT_VIOLATION
    elif not budget.authoritative or budget.budget_lkr is None or any(c.status == "UNKNOWN" and c.requirement == "Generated layout satisfies Agent 3 constraints" for c in checks):
        category = Eligibility.INSUFFICIENT_EVIDENCE
    elif unknown:
        category = Eligibility.CONDITIONAL
    else:
        category = Eligibility.ELIGIBLE
    return EligibilityAssessment(eligibility=category, checks=checks,
        unmet_requirements=unmet, uncertainty=sorted(set(unknown)))


def assess_eligibility(candidate, req):
    prop, budget, plan = candidate.property, candidate.budget, candidate.planning
    land = req.intent in {"BUY_LAND", "LAND_AND_HOUSE"}
    combined = req.intent == "LAND_AND_HOUSE"
    checks = budget_checks(budget)
    expected_listing = "rent" if req.intent == "RENT_PROPERTY" or req.listing_type == "rent" else "sale"
    checks.append(check("requirements", f"Listing type is {expected_listing}",
        None if not prop.listing_type else prop.listing_type.lower() == expected_listing, "Agent 2 listing_type"))
    expected_type = "land" if land else req.property_type
    if expected_type:
        checks.append(check("requirements", f"Property type is {expected_type}",
            None if not prop.property_type else prop.property_type.lower() in PROPERTY_TYPES.get(expected_type, {expected_type}), "Agent 2 property_type"))
    for field in ("location", "district"):
        requested = getattr(req, field)
        if requested:
            values = [getattr(prop, field)]
            if field == "location":
                values.append(prop.address)
            known = [v.casefold() for v in values if v and v.strip()]
            checks.append(check("location", f"{field} matches {requested}",
                None if not known else any(requested.strip().casefold() in v for v in known), f"Listing {field}/address evidence"))
    if req.minimum_budget_lkr is not None:
        checks.append(minimum_check("budget", "listing price (LKR)", req.minimum_budget_lkr, budget.price_lkr))
    if combined and req.maximum_land_budget_lkr is not None:
        checks.append(check("budget", "Land price fits original land budget", None if budget.price_lkr is None else budget.price_lkr <= req.maximum_land_budget_lkr, "Agent 2 total sale price"))
    if req.intent == "BUY_LAND" and req.maximum_budget_lkr is not None:
        checks.append(check("budget", "Land price also fits original purchase budget", None if budget.price_lkr is None else budget.price_lkr <= req.maximum_budget_lkr, "Original maximum_budget_lkr"))
    if combined:
        if req.total_project_budget_lkr is not None and budget.price_lkr is not None:
            checks.append(check("budget", "Land price alone fits total project budget",
                budget.price_lkr <= req.total_project_budget_lkr, "Agent 2 total sale price"))
        if req.construction_budget_lkr is not None:
            checks.append(check("budget", "Construction estimate fits original construction budget",
                None if not budget.authoritative or budget.construction is None else budget.construction.expected_lkr <= req.construction_budget_lkr,
                "Agent 3 construction expected estimate and original construction budget"))
    if not land:
        for field in ("bedrooms", "bathrooms"):
            if getattr(req, field) is not None:
                checks.append(minimum_check("requirements", field, getattr(req, field), getattr(prop, field)))
        for field in ("parking_spaces", "floors"):
            if getattr(req, field) is not None:
                checks.append(minimum_check("requirements", field, getattr(req, field), None))
    min_land = req.minimum_land_size_perches if req.minimum_land_size_perches is not None else req.land_size_perches
    if min_land is not None:
        checks.append(minimum_check("size", "land size (perches)", min_land, prop.land_size_perches))
    if req.maximum_land_size_perches is not None:
        size = number(prop.land_size_perches, positive=True)
        checks.append(check("size", f"Land size at most {req.maximum_land_size_perches} perches", None if size is None else size <= req.maximum_land_size_perches, "Agent 2 land_size_perches"))
    if not land and req.minimum_house_size_sqft is not None:
        checks.append(minimum_check("size", "house size (sq ft)", req.minimum_house_size_sqft, prop.house_size_sqft))
    if combined:
        checks.extend(planning_checks(req, plan))
        if plan and plan.land_size_perches is not None and prop.land_size_perches is not None:
            if abs(plan.land_size_perches - prop.land_size_perches) > .01:
                checks.append(check("planning", "Planning land area matches retrieved listing", None, "Conflicting upstream land areas"))
    # A land advertisement cannot establish the future house's style or rooms.
    if combined:
        property_preferences = req.model_copy(update={"preferred_style": None, "finish_level": None,
            "office_required": None, "balcony_required": None, "family_lounge_required": None,
            "utility_room_required": None})
        checks.extend(preference_checks(property_preferences, prop.features))
        planning_preferences = req.model_copy(update={"preferences": []})
        checks.extend(preference_checks(planning_preferences, None))
    else:
        checks.extend(preference_checks(req, prop.features))
    return classify_checks(checks, budget, uncertainty=candidate.uncertainty)
