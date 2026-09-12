from app.agents.agent1_requirements.extractor import extract_requirements, parse_money
from app.schemas.requirements import Intent, ListingType, PropertyType


def test_parse_sri_lankan_money_expressions() -> None:
    assert parse_money("Rs. 35 million")[0][2] == 35_000_000
    assert parse_money("35M")[0][2] == 35_000_000
    assert parse_money("12.5 Mn")[0][2] == 12_500_000
    assert parse_money("150k")[0][2] == 150_000
    assert parse_money("LKR 40 million")[0][2] == 40_000_000
    assert parse_money("Rs. 150,000")[0][2] == 150_000
    assert parse_money("Rs. three million")[0][2] == 3_000_000
    assert parse_money("below three million")[0][2] == 3_000_000
    assert parse_money("below thirteen million rupees")[0][2] == 13_000_000
    assert parse_money("රුපියල් මිලියන තුනකට අඩුවෙන්")[0][2] == 3_000_000
    assert parse_money("රුපියල් ලක්ෂ දෙකකට අඩුවෙන්")[0][2] == 200_000


def test_extract_buy_property_requirements() -> None:
    data = extract_requirements("Find me a 3-bedroom house in Kottawa below Rs. 35 million.", Intent.BUY_PROPERTY)

    assert data["location"] == "Kottawa"
    assert data["maximum_budget_lkr"] == 35_000_000
    assert data["property_type"] == PropertyType.HOUSE
    assert data["listing_type"] == ListingType.SALE
    assert data["bedrooms"] == 3


def test_extract_sinhala_singlish_buy_property_requirements() -> None:
    data = extract_requirements(
        "මට Kottawa අවට Rs. 35 million ට අඩුවෙන් 3-bedroom house එකක් ගන්න ඕන.",
        Intent.BUY_PROPERTY,
    )

    assert data["location"] == "Kottawa"
    assert data["maximum_budget_lkr"] == 35_000_000
    assert data["property_type"] == PropertyType.HOUSE
    assert data["listing_type"] == ListingType.SALE
    assert data["bedrooms"] == 3


def test_extract_word_budget_buy_property_requirements() -> None:
    data = extract_requirements(
        "Find me a five-bedroom house in Maharagama below Rs. three million.",
        Intent.BUY_PROPERTY,
    )

    assert data["location"] == "Maharagama"
    assert data["maximum_budget_lkr"] == 3_000_000
    assert data["property_type"] == PropertyType.HOUSE
    assert data["listing_type"] == ListingType.SALE
    assert data["bedrooms"] == 5


def test_extract_word_budget_without_money_sign() -> None:
    data = extract_requirements(
        "Find me a five-bedroom house in Maharagama below thirteen million rupees.",
        Intent.BUY_PROPERTY,
    )

    assert data["location"] == "Maharagama"
    assert data["maximum_budget_lkr"] == 13_000_000
    assert data["bedrooms"] == 5


def test_extract_full_sinhala_buy_property_requirements() -> None:
    data = extract_requirements(
        "මට මහරගම අවට රුපියල් මිලියන තුනකට අඩුවෙන් කාමර පහක නිවසක් ගන්න ඕන.",
        Intent.BUY_PROPERTY,
    )

    assert data["location"] == "Maharagama"
    assert data["maximum_budget_lkr"] == 3_000_000
    assert data["property_type"] == PropertyType.HOUSE
    assert data["listing_type"] == ListingType.SALE
    assert data["bedrooms"] == 5


def test_extract_full_sinhala_preferences_and_district() -> None:
    data = extract_requirements(
        "මට කොට්ටාව අවට නිහඬ පරිසරයක, පහසු සහ සුවපහසු නිවසක් ගන්න ඕන. රුපියල් මිලියන පහකට අඩුවෙන්.",
        Intent.BUY_PROPERTY,
    )

    assert data["location"] == "Kottawa"
    assert data["district"] == "Colombo"
    assert data["maximum_budget_lkr"] == 5_000_000
    assert data["property_type"] == PropertyType.HOUSE
    assert data["listing_type"] == ListingType.SALE
    assert data["preferences"] == ["quiet environment", "comfortable environment", "convenient access"]


def test_extract_full_sinhala_rent_property_requirements() -> None:
    data = extract_requirements(
        "මට කොළඹ රුපියල් ලක්ෂ දෙකකට අඩුවෙන් මහල් නිවාසයක් කුලියට ඕන.",
        Intent.RENT_PROPERTY,
    )

    assert data["location"] == "Colombo"
    assert data["maximum_budget_lkr"] == 200_000
    assert data["property_type"] == PropertyType.APARTMENT
    assert data["listing_type"] == ListingType.RENT


def test_extract_plan_house_requirements() -> None:
    data = extract_requirements(
        "I have 15 perches in Malabe and want to build a four-bedroom two-storey house.",
        Intent.PLAN_HOUSE,
    )

    assert data["location"] == "Malabe"
    assert data["land_size_perches"] == 15
    assert data["bedrooms"] == 4
    assert data["floors"] == 2


def test_extract_full_sinhala_plan_house_requirements() -> None:
    data = extract_requirements(
        "මට මාලඹේ පර්චස් පහළොවක ඉඩමක් තියෙනවා, කාමර හතරක මහල් දෙකක නිවසක් හදන්න ඕන.",
        Intent.PLAN_HOUSE,
    )

    assert data["location"] == "Malabe"
    assert data["land_size_perches"] == 15
    assert data["bedrooms"] == 4
    assert data["floors"] == 2


def test_extract_parking_requirements() -> None:
    data = extract_requirements("Need a modern house with two-car parking and balcony.", Intent.PLAN_HOUSE)

    assert data["parking_spaces"] == 2
    assert data["balcony_required"] is True
    assert data["preferred_style"] == "modern"
