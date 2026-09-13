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

