from app.agents.agent1_requirements.intent_classifier import classify_intent
from app.schemas.requirements import Intent


def test_buy_property_intent() -> None:
    assert classify_intent("Find me a 3-bedroom house in Kottawa below Rs. 35 million.") == Intent.BUY_PROPERTY


def test_sinhala_singlish_buy_property_intent() -> None:
    assert (
        classify_intent("මට Kottawa අවට Rs. 35 million ට අඩුවෙන් 3-bedroom house එකක් ගන්න ඕන.")
        == Intent.BUY_PROPERTY
    )


def test_full_sinhala_buy_property_intent() -> None:
    assert classify_intent("මට මහරගම අවට රුපියල් මිලියන තුනකට අඩුවෙන් කාමර පහක නිවසක් ගන්න ඕන.") == Intent.BUY_PROPERTY


def test_rent_property_intent() -> None:
    assert classify_intent("I want an apartment for rent in Colombo below Rs. 150,000 per month.") == Intent.RENT_PROPERTY


def test_full_sinhala_rent_property_intent() -> None:
    assert classify_intent("මට කොළඹ රුපියල් ලක්ෂ දෙකකට අඩුවෙන් මහල් නිවාසයක් කුලියට ඕන.") == Intent.RENT_PROPERTY


def test_plan_house_intent() -> None:
    assert classify_intent("I have 15 perches in Malabe and want to build a four-bedroom two-storey house.") == Intent.PLAN_HOUSE


def test_full_sinhala_plan_house_intent() -> None:
    assert (
        classify_intent("මට මාලඹේ පර්චස් පහළොවක ඉඩමක් තියෙනවා, කාමර හතරක මහල් දෙකක නිවසක් හදන්න ඕන.")
        == Intent.PLAN_HOUSE
    )


def test_land_and_house_intent() -> None:
    query = "I have Rs. 40 million total. Find land around Kottawa and determine whether I can build a 3-bedroom two-storey house."
    assert classify_intent(query) == Intent.LAND_AND_HOUSE


def test_full_sinhala_land_and_house_intent() -> None:
    query = "මට කොට්ටාව අවට රුපියල් මිලියන 40ක මුළු බජට් එකක් තියෙනවා. ඉඩමක් හොයාගෙන කාමර 2ක නිවසක් හදන්න පුළුවන්ද බලන්න."
    assert classify_intent(query) == Intent.LAND_AND_HOUSE


def test_full_sinhala_land_buy_and_build_intent() -> None:
    assert classify_intent("මට නුවරින් මිලියන 40ට අඩුවෙන් ඉඩමක් අරන් ගෙයක් හදන්න ඕන") == Intent.LAND_AND_HOUSE


def test_compare_properties_intent() -> None:
    assert classify_intent("Compare these properties.") == Intent.COMPARE_PROPERTIES
