import re

from app.schemas.requirements import Intent


def classify_intent(query: str) -> Intent:
    text = query.lower()

    if re.search(r"\b(compare|comparison|which one|better option)\b", text) or re.search(r"(සසඳ|සන්සන්දනය)", query):
        return Intent.COMPARE_PROPERTIES

    mentions_land = re.search(r"\b(land|plot)\b", text) is not None or re.search(r"(ඉඩම|ඉඩමක්)", query) is not None
    mentions_building = re.search(r"\b(build|construct|planning|plan|house design|home plan)\b", text) is not None or re.search(
        r"(හදන්න|සාදන්න|ඉදිකරන්න|නිවසක් හද|ගෙයක් හද|සැලසුම්)",
        query,
    ) is not None
    mentions_house_program = re.search(r"\b(?:\d+|one|two|three|four|five|six)[-\s]*(?:bedroom|bed)\s+(?:house|home)\b", text) is not None
    wants_to_buy = re.search(r"\b(find|buy|search|look for|purchase)\b", text) is not None or re.search(
        r"(ගන්න|මිලදී|විකිණීමට)", query
    ) is not None
    wants_land_search = wants_to_buy and mentions_land

    if mentions_land and (mentions_building or mentions_house_program) and (wants_land_search or re.search(r"\btotal\s+budget\b", text)):
        return Intent.LAND_AND_HOUSE

    if mentions_building:
        return Intent.PLAN_HOUSE

    if re.search(r"\b(rent|rental|per month|monthly)\b", text) or re.search(r"(කුලියට|මාසික)", query):
        return Intent.RENT_PROPERTY

    if re.search(r"\b(estimate|budget|cost|price range|afford)\b", text) and not re.search(
        r"\b(find|buy|purchase)\b", text
    ) or re.search(r"(වියදම|අයවැය|ඇස්තමේන්තු)", query):
        return Intent.ESTIMATE_BUDGET

    if wants_to_buy and mentions_land:
        return Intent.BUY_LAND

    if wants_to_buy:
        return Intent.BUY_PROPERTY

    if re.search(r"\b(property|house|apartment|land|commercial|real estate)\b", text) or re.search(
        r"(දේපල|නිවස|ගෙයක්|මහල් නිවාස|ඉඩම)",
        query,
    ):
        return Intent.GENERAL_PROPERTY_QUERY

    return Intent.UNKNOWN
