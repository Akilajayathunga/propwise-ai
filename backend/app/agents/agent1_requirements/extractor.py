import re

from app.schemas.requirements import Intent, ListingType, PropertyType


NUMBER_WORDS = {
    "zero": 0,
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
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
    "එක": 1,
    "එක්": 1,
    "දෙක": 2,
    "දෙ": 2,
    "තුන": 3,
    "හතර": 4,
    "පහ": 5,
    "හය": 6,
    "හත": 7,
    "අට": 8,
    "නවය": 9,
    "දහය": 10,
    "එකොළහ": 11,
    "දොළහ": 12,
    "දහතුන": 13,
    "දාහතර": 14,
    "පහළොව": 15,
    "දහසය": 16,
    "දහහත": 17,
    "දහඅට": 18,
    "දහනවය": 19,
    "විස්ස": 20,
    "තිහ": 30,
    "හතළිහ": 40,
    "පනහ": 50,
}

NUMBER_WORD_PATTERN = (
    r"zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|"
    r"fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|"
    r"eighty|ninety|එක|එක්|දෙක|දෙ|තුන|හතර|පහ|හය|හත|අට|නවය|දහය|එකොළහ|දොළහ|දහතුන|"
    r"දාහතර|පහළොව|දහසය|දහහත|දහඅට|දහනවය|විස්ස|තිහ|හතළිහ|පනහ"
)
NUMBER_PATTERN = rf"(?P<number>\d+(?:\.\d+)?|{NUMBER_WORD_PATTERN})"

KNOWN_SRI_LANKAN_LOCATIONS = {
    "කොට්ටාව": "Kottawa",
    "මහරගම": "Maharagama",
    "කොළඹ": "Colombo",
    "මාලඹේ": "Malabe",
}


def word_or_number(value: str) -> float:
    normalized = value.lower()
    if normalized in NUMBER_WORDS:
        return float(NUMBER_WORDS[normalized])
    return float(normalized)


def parse_number_words(value: str) -> float | None:
    normalized = value.lower().replace("-", " ").strip()
    if not normalized:
        return None
    if re.fullmatch(r"\d+(?:,\d{3})*(?:\.\d+)?", normalized):
        return float(normalized.replace(",", ""))

    total = 0
    current = 0
    found = False
    for token in normalized.split():
        token = re.sub(r"(කට|ක්|ක|ට)$", "", token)
        if token in {"and", "යි"}:
            continue
        if token in NUMBER_WORDS:
            current += NUMBER_WORDS[token]
            found = True
        elif token == "hundred" and current:
            current *= 100
            found = True
        else:
            return None
    if not found:
        return None
    return float(total + current)


def to_int(value: float | None) -> int | None:
    if value is None:
        return None
    return int(value)


def parse_money(text: str) -> list[tuple[int, int, int]]:
    numeric_pattern = re.compile(
        r"(?:(?:rs\.?|lkr|රුපියල්)\s*)?"
        r"(?P<amount>\d+(?:,\d{3})*(?:\.\d+)?)\s*"
        r"(?P<unit>million|mn|m|k|thousand|lakh|lakhs|rupees?|lkr|මිලියන|දහස|ලක්ෂ|රුපියල්)?",
        re.IGNORECASE,
    )
    values = []
    for match in numeric_pattern.finditer(text):
        unit = (match.group("unit") or "").lower()
        following_text = text[match.end() : match.end() + 24].lower()
        if re.match(r"\s*-?\s*(bedroom|bedrooms|bed|bathroom|bathrooms|bath|storey|story|floor|floors|perch|perches)", following_text):
            continue
        has_currency = re.search(r"\b(rs\.?|lkr)\b|රුපියල්", match.group(0), re.IGNORECASE) or re.search(
            r"(rs\.?|lkr|රුපියල්)\s*$",
            text[max(0, match.start() - 8) : match.start()],
            re.IGNORECASE,
        )
        has_budget_cue = re.search(
            r"(\b(below|under|less than|above|over|minimum|min|from|at least|budget|price|cost|total)\b|අඩුවෙන්|අඩු|වැඩි|අවම|මුළු|සම්පූර්ණ)\s*$",
            text[max(0, match.start() - 24) : match.start()].lower(),
        )
        if not has_currency and not unit and not has_budget_cue:
            continue
        amount = float(match.group("amount").replace(",", ""))
        multiplier = 1
        if unit in {"million", "mn", "m", "මිලියන"}:
            multiplier = 1_000_000
        elif unit in {"k", "thousand", "දහස"}:
            multiplier = 1_000
        elif unit in {"lakh", "lakhs", "ලක්ෂ"}:
            multiplier = 100_000
        values.append((match.start(), match.end(), int(amount * multiplier)))

    word_pattern = re.compile(
        rf"(?:(?:rs\.?|lkr|රුපියල්)\s*)?"
        rf"(?P<amount>(?:{NUMBER_WORD_PATTERN})(?:[-\s]+(?:and\s+)?(?:{NUMBER_WORD_PATTERN}|hundred))*)\s*"
        r"(?P<unit>million|mn|thousand|lakh|lakhs|rupees?|මිලියන|දහස|ලක්ෂ|රුපියල්)(?:කට|ක්|ක|ට)?",
        re.IGNORECASE,
    )
    for match in word_pattern.finditer(text):
        unit = match.group("unit").lower()
        amount = parse_number_words(match.group("amount"))
        if amount is None:
            continue
        multiplier = 1
        if unit in {"million", "mn", "මිලියන"}:
            multiplier = 1_000_000
        elif unit in {"thousand", "දහස"}:
            multiplier = 1_000
        elif unit in {"lakh", "lakhs", "ලක්ෂ"}:
            multiplier = 100_000
        values.append((match.start(), match.end(), int(amount * multiplier)))

    sinhala_unit_first_pattern = re.compile(
        rf"(?:රුපියල්\s*)?"
        r"(?P<unit>මිලියන|දහස|ලක්ෂ)\s*"
        rf"(?P<amount>\d+(?:,\d{{3}})*(?:\.\d+)?|{NUMBER_WORD_PATTERN})(?:කට|ක්|ක|ට)?",
        re.IGNORECASE,
    )
    for match in sinhala_unit_first_pattern.finditer(text):
        unit = match.group("unit").lower()
        amount = parse_number_words(match.group("amount"))
        if amount is None:
            continue
        multiplier = 1
        if unit == "මිලියන":
            multiplier = 1_000_000
        elif unit == "දහස":
            multiplier = 1_000
        elif unit == "ලක්ෂ":
            multiplier = 100_000
        values.append((match.start(), match.end(), int(amount * multiplier)))

    values.sort(key=lambda item: item[0])
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
        if re.search(r"\b(total|overall|entire project)\b|මුළු|සම්පූර්ණ", window):
            result["total_project_budget_lkr"] = value
        elif re.search(r"\b(construction|build|building)\b|ඉදිකිරීම්|හදන්න|සාදන්න", window):
            result["construction_budget_lkr"] = value
        elif re.search(r"\b(above|over|minimum|min|from|at least)\b|වැඩි|අවම", window):
            result["minimum_budget_lkr"] = value
        else:
            result["maximum_budget_lkr"] = value
    return result


def extract_location(text: str) -> str | None:
    for sinhala_name, normalized_name in KNOWN_SRI_LANKAN_LOCATIONS.items():
        if sinhala_name in text:
            return normalized_name

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
        rf"\b{NUMBER_PATTERN}(?:කට|ක්|ක|ට)?[-\s]*(?:{noun_pattern})\b",
        rf"\b(?:{noun_pattern})\s*(?:for|:)?\s*{NUMBER_PATTERN}(?:කට|ක්|ක|ට)?\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return to_int(word_or_number(match.group("number")))
    return None


def extract_floors(text: str) -> int | None:
    patterns = [
        rf"\b{NUMBER_PATTERN}(?:කට|ක්|ක|ට)?[-\s]*(?:storey|story|stories|floor|floors|මහල්|තට්ටු)\b",
        rf"\b(?:මහල්|තට්ටු)\s*{NUMBER_PATTERN}(?:කට|ක්|ක|ට)?\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return to_int(word_or_number(match.group("number")))
    return None


def extract_land_size(text: str) -> float | None:
    patterns = [
        rf"\b{NUMBER_PATTERN}(?:කට|ක්|ක|ට)?\s*(?:perches|perch|පර්චස්)\b",
        rf"\b(?:perches|perch|පර්චස්)\s*{NUMBER_PATTERN}(?:කට|ක්|ක|ට)?\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
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
    if re.search(r"\b(apartment|flat|condo)\b", lower) or re.search(r"(මහල් නිවාස|අපාර්ට්මන්ට්)", text):
        return PropertyType.APARTMENT
    if re.search(r"\b(room|annex|annexe)\b", lower) or re.search(r"(කාමරයක්|ඇනෙක්ස්)", text):
        return PropertyType.ROOM_ANNEX
    if re.search(r"\b(commercial|shop|office space|warehouse)\b", lower) or re.search(r"(වාණිජ|කඩ|ගබඩා)", text):
        return PropertyType.COMMERCIAL
    if re.search(r"\b(land|plot)\b", lower) or re.search(r"(ඉඩම|ඉඩමක්)", text):
        return PropertyType.LAND
    if re.search(r"\b(house|home|villa)\b", lower) or re.search(r"(නිවස|නිවසක්|ගෙයක්|ගේ)", text):
        return PropertyType.HOUSE
    if intent == Intent.PLAN_HOUSE:
        return PropertyType.HOUSE
    return None


def extract_listing_type(text: str, intent: Intent) -> ListingType | None:
    lower = text.lower()
    if re.search(r"\b(rent|rental|per month|monthly)\b", lower) or re.search(r"(කුලියට|මාසික)", text):
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
        "bedrooms": extract_count(query, ("bedroom", "bedrooms", "bed", "කාමර", "කාමරය")),
        "bathrooms": extract_count(query, ("bathroom", "bathrooms", "bath", "නාන කාමර", "නානකාමර")),
        "land_size_perches": extract_land_size(query),
        "minimum_house_size_sqft": extract_house_size(query),
        "floors": extract_floors(query),
        "parking_spaces": extract_count(query, ("car parking", "cars", "parking spaces", "parking")),
    }
    data.update(extract_budget(query))
    data.update(extract_flags(query))
    data.update(extract_text_preferences(query))
    return data
