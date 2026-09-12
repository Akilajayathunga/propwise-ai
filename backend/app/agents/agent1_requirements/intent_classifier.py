import re

from app.schemas.requirements import Intent


def classify_intent(query: str) -> Intent:
    text = query.lower()

    if re.search(r"\b(compare|comparison|which one|better option)\b", text):
        return Intent.COMPARE_PROPERTIES

    mentions_land = re.search(r"\b(land|plot)\b", text) is not None
    mentions_building = re.search(r"\b(build|construct|planning|plan|house design|home plan)\b", text) is not None
    wants_to_buy = re.search(r"\b(find|buy|search|look for|purchase)\b", text) is not None or re.search(
        r"(ගන්න|මිලදී|විකිණීමට)", query
    ) is not None
    wants_land_search = wants_to_buy and mentions_land

    if mentions_land and mentions_building and wants_land_search:
        return Intent.LAND_AND_HOUSE

    if mentions_building:
        return Intent.PLAN_HOUSE

    if re.search(r"\b(rent|rental|per month|monthly)\b", text):
        return Intent.RENT_PROPERTY

    if re.search(r"\b(estimate|budget|cost|price range|afford)\b", text) and not re.search(
        r"\b(find|buy|purchase)\b", text
    ):
        return Intent.ESTIMATE_BUDGET

    if wants_to_buy and mentions_land:
        return Intent.BUY_LAND

    if wants_to_buy:
        return Intent.BUY_PROPERTY

    if re.search(r"\b(property|house|apartment|land|commercial|real estate)\b", text):
        return Intent.GENERAL_PROPERTY_QUERY

    return Intent.UNKNOWN
