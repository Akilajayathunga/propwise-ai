from app.agents.agent1_requirements.extractor import extract_requirements, parse_money
from app.schemas.requirements import Intent, ListingType, PropertyType


def test_parse_sri_lankan_money_expressions() -> None:
    assert parse_money("Rs. 35 million")[0][2] == 35_000_000
    assert parse_money("35M")[0][2] == 35_000_000
    assert parse_money("12.5 Mn")[0][2] == 12_500_000
    assert parse_money("150k")[0][2] == 150_000
    assert parse_money("LKR 40 million")[0][2] == 40_000_000
    assert parse_money("Rs. 150,000")[0][2] == 150_000


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


def test_extract_plan_house_requirements() -> None:
    data = extract_requirements(
        "I have 15 perches in Malabe and want to build a four-bedroom two-storey house.",
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
