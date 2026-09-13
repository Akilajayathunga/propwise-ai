from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_generate_planning_endpoint() -> None:
    response = client.post(
        "/api/v1/planning/generate",
        json={
            "intent": "PLAN_HOUSE",
            "location": "Malabe",
            "land_size_perches": 15,
            "bedrooms": 4,
            "bathrooms": 3,
            "floors": 2,
            "parking_spaces": 2,
            "office_required": True,
            "balcony_required": True,
            "candidate_count": 2,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["constraints_satisfied"] is True
    assert body["plan_id"].startswith("plan-")
    assert body["files"]["json"]
    assert body["files"]["svg"]
    assert body["files"]["png"]
    assert body["files"]["dxf"]


def test_evaluate_land_house_returns_combined_options_with_preserved_house_requirements() -> None:
    response = client.post(
        "/api/v1/planning/evaluate-land-house",
        json={
            "requirements": {
                "original_query": "I want land in Kottawa and a 2-bedroom house. My total budget is 40 million.",
                "intent": "LAND_AND_HOUSE",
                "location": "Kottawa",
                "district": "Colombo",
                "total_project_budget_lkr": 40_000_000,
                "property_type": "land",
                "listing_type": "sale",
                "bedrooms": 2,
                "preferences": [],
                "missing_information": [],
                "confidence": 0.8,
            },
            "property_results": [
                {
                    "listing_id": "land-kottawa-test",
                    "title": "Kottawa land",
                    "location": "Kottawa",
                    "district": "Colombo",
                    "listing_type": "sale",
                    "property_type": "land",
                    "land_size_perches": 11,
                    "sale_total_price_lkr": 9_500_000,
                    "score": 0.63,
                }
            ],
        },
    )

    assert response.status_code == 200
    option = response.json()["options"][0]
    assert option["property"]["listing_id"] == "land-kottawa-test"
    assert option["house"]["bedrooms"] == 2
    assert option["house"]["bathrooms"] == 1
    assert option["house"]["floors"] == 1
    assert option["budget"]["land_price_lkr"] == 9_500_000
    assert option["budget"]["remaining_after_land_lkr"] == 30_500_000
    assert option["planning"]["plan_id"].startswith("plan-")
    assert option["planning"]["svg_url"]
