from app.schemas.requirements import Intent, ParsedRequirements


REQUIRED_BY_INTENT = {
    Intent.BUY_PROPERTY: ["location", "maximum_budget_lkr", "property_type"],
    Intent.RENT_PROPERTY: ["location", "maximum_budget_lkr", "property_type"],
    Intent.BUY_LAND: ["location", "maximum_budget_lkr"],
    Intent.PLAN_HOUSE: ["location", "land_size_perches", "bedrooms"],
    Intent.LAND_AND_HOUSE: ["location", "total_project_budget_lkr", "bedrooms"],
}


def validate_requirements(requirements: ParsedRequirements) -> ParsedRequirements:
    missing = []
    for field_name in REQUIRED_BY_INTENT.get(Intent(requirements.intent), []):
        if getattr(requirements, field_name) is None:
            missing.append(field_name)

    confidence = calculate_confidence(requirements, missing)
    return requirements.model_copy(update={"missing_information": missing, "confidence": confidence})


def calculate_confidence(requirements: ParsedRequirements, missing: list[str]) -> float:
    score = 0.35 if requirements.intent != Intent.UNKNOWN else 0.1
    useful_fields = [
        "location",
        "minimum_budget_lkr",
        "maximum_budget_lkr",
        "total_project_budget_lkr",
        "construction_budget_lkr",
        "property_type",
        "listing_type",
        "bedrooms",
        "bathrooms",
        "land_size_perches",
        "floors",
        "parking_spaces",
    ]
    populated = sum(1 for field_name in useful_fields if getattr(requirements, field_name) is not None)
    score += min(0.55, populated * 0.06)
    score -= min(0.25, len(missing) * 0.05)
    return round(max(0.0, min(0.95, score)), 2)

