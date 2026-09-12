import re

from app.schemas.requirements import Intent, ListingType, PropertyType


NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}

NUMBER_PATTERN = r"(?P<number>\d+(?:\.\d+)?|one|two|three|four|five|six|seven|eight|nine|ten)"


def word_or_number(value: str) -> float:
    normalized = value.lower()
    if normalized in NUMBER_WORDS:
        return float(NUMBER_WORDS[normalized])
    return float(normalized)


def to_int(value: float | None) -> int | None:
    if value is None:
        return None
    return int(value)


def parse_money(text: str) -> list[tuple[int, int, int]]:
    pattern = re.compile(
        r"(?:(?:rs\.?|lkr)\s*)?"
        r"(?P<amount>\d+(?:,\d{3})*(?:\.\d+)?)\s*"
        r"(?P<unit>million|mn|m|k|thousand|lakh|lakhs)?",
        re.IGNORECASE,
    )
    values = []
    for match in pattern.finditer(text):
        unit = (match.group("unit") or "").lower()
        has_currency = re.search(r"\b(rs\.?|lkr)\b", match.group(0), re.IGNORECASE) or re.search(
            r"(rs\.?|lkr)\s*$",
            text[max(0, match.start() - 8) : match.start()],
            re.IGNORECASE,
        )
        if not has_currency and not unit:
            continue
        amount = float(match.group("amount").replace(",", ""))
        multiplier = 1
        if unit in {"million", "mn", "m"}:
            multiplier = 1_000_000
        elif unit in {"k", "thousand"}:
            multiplier = 1_000
        elif unit in {"lakh", "lakhs"}:
            multiplier = 100_000
        values.append((match.start(), match.end(), int(amount * multiplier)))
    return values


def extract_budget(text: str) -> dict[str, int | None]:
    result = {
        "minimum_budget_lkr": None,
        "maximum_budget_lkr": None,
        "total_project_budget_lkr": None,
        "construction_budget_lkr": None,
    }
    for start, end, value in parse_money(text):
        window = text[max(0, start - 40) : min(len(text), end + 40)].lower()
        if re.search(r"\b(total|overall|entire project)\b", window):
            result["total_project_budget_lkr"] = value
        elif re.search(r"\b(construction|build|building)\b", window):
            result["construction_budget_lkr"] = value
        elif re.search(r"\b(above|over|minimum|min|from|at least)\b", window):
            result["minimum_budget_lkr"] = value
        else:
            result["maximum_budget_lkr"] = value
    return result


def extract_location(text: str) -> str | None:
    sinhala_marker_match = re.search(
        r"\b([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,2})\s*(?:අවට|ලග|ළඟ|තුල|වල)\b",
        text,
    )
    if sinhala_marker_match:
        return sinhala_marker_match.group(1).strip()

    match = re.search(
        r"\b(?:in|around|near|at|within)\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,2})\b",
        text,
    )
    if not match:
        return None
    location = match.group(1).strip()
    stop_words = {"and", "with", "below", "under", "for", "to", "that", "determine"}
    parts = [part for part in location.split() if part.lower() not in stop_words]
    return " ".join(parts) or None


def extract_count(text: str, nouns: tuple[str, ...]) -> int | None:
    noun_pattern = "|".join(re.escape(noun) for noun in nouns)
    patterns = [
        rf"\b{NUMBER_PATTERN}[-\s]*(?:{noun_pattern})\b",
        rf"\b(?:{noun_pattern})\s*(?:for|:)?\s*{NUMBER_PATTERN}\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return to_int(word_or_number(match.group("number")))
    return None


def extract_floors(text: str) -> int | None:
    match = re.search(rf"\b{NUMBER_PATTERN}[-\s]*(?:storey|story|stories|floor|floors)\b", text, re.IGNORECASE)
    if match:
        return to_int(word_or_number(match.group("number")))
    return None


def extract_land_size(text: str) -> float | None:
    match = re.search(rf"\b{NUMBER_PATTERN}\s*(?:perches|perch)\b", text, re.IGNORECASE)
    if match:
        value = word_or_number(match.group("number"))
        return int(value) if value.is_integer() else value
    return None


def extract_house_size(text: str) -> int | None:
    match = re.search(rf"\b(?:at least|minimum|min)?\s*{NUMBER_PATTERN}\s*(?:sqft|sq ft|square feet)\b", text, re.IGNORECASE)
    if match:
        return to_int(word_or_number(match.group("number")))
    return None


def extract_property_type(text: str, intent: Intent) -> PropertyType | None:
    lower = text.lower()
    if re.search(r"\b(apartment|flat|condo)\b", lower):
        return PropertyType.APARTMENT
    if re.search(r"\b(room|annex|annexe)\b", lower):
        return PropertyType.ROOM_ANNEX
    if re.search(r"\b(commercial|shop|office space|warehouse)\b", lower):
        return PropertyType.COMMERCIAL
    if re.search(r"\b(land|plot)\b", lower):
        return PropertyType.LAND
    if re.search(r"\b(house|home|villa)\b", lower):
        return PropertyType.HOUSE
    if intent == Intent.PLAN_HOUSE:
        return PropertyType.HOUSE
    return None


def extract_listing_type(text: str, intent: Intent) -> ListingType | None:
    lower = text.lower()
    if re.search(r"\b(rent|rental|per month|monthly)\b", lower):
        return ListingType.RENT
    if intent in {Intent.BUY_PROPERTY, Intent.BUY_LAND, Intent.LAND_AND_HOUSE}:
        return ListingType.SALE
    if re.search(r"\b(buy|purchase|sale|for sale)\b", lower) or re.search(r"(ගන්න|මිලදී|විකිණීමට)", text):
        return ListingType.SALE
    return None


def extract_flags(text: str) -> dict[str, bool | None]:
    lower = text.lower()
    return {
        "office_required": True if re.search(r"\b(home office|office room|study room|workspace)\b", lower) else None,
        "balcony_required": True if re.search(r"\bbalcony\b", lower) else None,
        "family_lounge_required": True if re.search(r"\b(family lounge|tv lounge)\b", lower) else None,
        "utility_room_required": True if re.search(r"\b(utility room|laundry room)\b", lower) else None,
    }


def extract_text_preferences(text: str) -> dict[str, str | None]:
    lower = text.lower()
    preferred_style = None
    for style in ("modern", "traditional", "minimalist", "luxury", "colonial"):
        if re.search(rf"\b{style}\b", lower):
            preferred_style = style
            break

    finish_level = None
    for level in ("basic", "standard", "premium", "luxury"):
        if re.search(rf"\b{level}\s+(?:finish|finishing|level)\b", lower):
            finish_level = level
            break

    return {"preferred_style": preferred_style, "finish_level": finish_level}


def extract_requirements(query: str, intent: Intent) -> dict[str, object]:
    data: dict[str, object] = {
        "location": extract_location(query),
        "property_type": extract_property_type(query, intent),
        "listing_type": extract_listing_type(query, intent),
        "bedrooms": extract_count(query, ("bedroom", "bedrooms", "bed")),
        "bathrooms": extract_count(query, ("bathroom", "bathrooms", "bath")),
        "land_size_perches": extract_land_size(query),
        "minimum_house_size_sqft": extract_house_size(query),
        "floors": extract_floors(query),
        "parking_spaces": extract_count(query, ("car parking", "cars", "parking spaces", "parking")),
    }
    data.update(extract_budget(query))
    data.update(extract_flags(query))
    data.update(extract_text_preferences(query))
    return data
