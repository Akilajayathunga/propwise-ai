"""Phase 3 integration tests. No live providers and no planning artifact writes."""
from unittest.mock import Mock

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.router import router
from app.api.v1.recommendation import get_recommendation_integration
from app.agents.agent4_recommendation import integration as module
from app.agents.agent4_recommendation import presentation
from app.agents.agent4_recommendation.explanations import ExplanationService
from app.agents.agent4_recommendation.integration import RecommendationIntegration
from app.schemas.recommendation_api import RecommendationRequest
from tests.test_agent4 import requirements, property_result, search, land, land_req, option, combined, owned_response
from tests.test_agent4_phase2 import FakeProvider


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    def forbidden(*args, **kwargs):
        raise AssertionError("Live provider transport is forbidden")
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    # Default provider is explicitly disabled, independent of real environment keys.
    monkeypatch.setattr(ExplanationService, "from_settings", classmethod(lambda cls: cls()))
    from app.agents.agent3_planning import agent as planning_agent
    monkeypatch.setattr(planning_agent, "STORAGE_ROOT", tmp_path / "plans")
    monkeypatch.setattr(presentation, "PLANS_ROOT", tmp_path / "plans")


@pytest.fixture
def api():
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return app


def body(req=None, **extra):
    return {"requirements": (req or requirements()).model_dump(mode="json"), "explanation_enabled": False, **extra}


def post(api, payload, service=None):
    if service is not None:
        api.dependency_overrides[get_recommendation_integration] = lambda: service
    with TestClient(api) as client:
        return client.post("/api/v1/recommendation", json=payload)


def service_for(props=None, **kwargs):
    return RecommendationIntegration(search=Mock(return_value=search(props or [])),
        direct_plan=kwargs.pop("direct_plan", Mock(return_value=owned_response())),
        combined_plan=kwargs.pop("combined_plan", Mock(return_value=combined())),
        **kwargs)


@pytest.mark.parametrize("intent,listing_type,property_type", [
    ("BUY_PROPERTY", "sale", "house"), ("RENT_PROPERTY", "rent", "house"),
    ("BUY_LAND", "sale", "land"), ("COMPARE_PROPERTIES", "sale", "house"),
])
def test_search_intents_use_only_agent2_then_agent4(api, intent, listing_type, property_type):
    prop = property_result(listing_type=listing_type, property_type=property_type, rent_monthly_lkr=70)
    service = service_for([prop])
    result = post(api, body(requirements(intent=intent, listing_type=listing_type, property_type=property_type)), service)
    assert result.status_code == 200
    data = result.json()
    assert data["recommendations"][0]["listing_id"] == prop.listing_id
    assert data["explanation_status"] == "DETERMINISTIC"
    assert service.search.call_args.kwargs["top_n"] == 30
    assert service.search.call_count == 1
    service.direct_plan.assert_not_called()
    service.combined_plan.assert_not_called()


def test_land_house_calls_combined_once_and_uses_final_agent4_order(api):
    a, b = land("a", score=.99), land("b", score=.1)
    service = service_for([a, b], combined_plan=Mock(return_value=combined(
        option(a, expected=90, high=100, combination=100), option(b, combination=1))))
    result = post(api, body(land_req()), service)
    assert result.status_code == 200
    data = result.json()
    assert data["recommendations"][0]["listing_id"] == "b"
    assert data["alternatives"][0]["listing_id"] == "a"
    assert service.combined_plan.call_count == 1
    service.direct_plan.assert_not_called()
    received = service.combined_plan.call_args.args[0]
    assert [p["listing_id"] for p in received.property_results] == ["a", "b"]


def test_owned_land_calls_direct_once_with_measured_dimensions(api):
    service = service_for()
    req = requirements(intent="PLAN_HOUSE", construction_budget_lkr=100, land_size_perches=10,
                       bedrooms=3, bathrooms=2, floors=1)
    result = post(api, body(req, owned_land={"land_width_ft": 50, "land_length_ft": 80}), service)
    assert result.status_code == 200
    assert result.json()["owned_land_assessment"]
    assert result.json()["recommendations"] == []
    assert service.direct_plan.call_count == 1
    passed = service.direct_plan.call_args.args[0]
    assert passed.land_width_ft == 50 and passed.land_length_ft == 80
    assert passed.selected_property is None
    service.search.assert_not_called()
    service.combined_plan.assert_not_called()


def test_missing_owned_site_data_clarifies_before_generating(api):
    service = service_for()
    req = requirements(intent="PLAN_HOUSE", construction_budget_lkr=100)
    result = post(api, body(req), service)
    assert result.status_code == 200
    assert result.json()["status"] == "NEEDS_CLARIFICATION"
    assert "owned_land.land_width_ft" in result.json()["clarification_fields"]
    service.direct_plan.assert_not_called()


@pytest.mark.parametrize("owned", [{"land_width_ft": -1}, {"land_length_ft": 0},
                                   {"land_width_ft": float("inf")}, {"land_price_lkr": 10},
                                   {"constraints_satisfied": True}, {"selected_property": {}}])
def test_invalid_owned_input_is_rejected(owned):
    req = requirements(intent="PLAN_HOUSE", construction_budget_lkr=100)
    with pytest.raises(ValueError):
        RecommendationRequest.model_validate(body(req, owned_land=owned))


def test_owned_context_on_wrong_workflow_is_422(api):
    assert post(api, body(owned_land={"land_width_ft": 50}), service_for()).status_code == 422


@pytest.mark.parametrize("extra", [
    {"final_score": 100}, {"rank": 1}, {"eligibility": "ELIGIBLE"},
    {"property_search": {"results": []}}, {"planning": {"constraints_satisfied": True}},
    {"land_house": {"options": []}}, {"response": {"status": "OK"}},
    {"property_results": [{"listing_id": "fake", "score": 1}]},
])
def test_fabricated_trusted_outputs_cannot_be_submitted(api, extra):
    service = service_for()
    result = post(api, body(**extra), service)
    assert result.status_code == 422
    service.search.assert_not_called()


@pytest.mark.parametrize("name", ["score", "sale_total_price_lkr", "combination_score", "constraints_satisfied", "property_results"])
def test_nested_fabricated_evidence_is_rejected(api, name):
    payload = body()
    payload["requirements"][name] = 100
    assert post(api, payload, service_for()).status_code == 422


@pytest.mark.parametrize("top_k", [0, 11, True, "3"])
def test_top_k_bounds_and_types(api, top_k):
    assert post(api, body(top_k=top_k), service_for()).status_code == 422


@pytest.mark.parametrize("intent", ["UNKNOWN", "ESTIMATE_BUDGET", "GENERAL_PROPERTY_QUERY", "not-an-intent"])
def test_unsupported_intents_return_422(api, intent):
    payload = body()
    payload["requirements"]["intent"] = intent
    assert post(api, payload, service_for()).status_code == 422


def test_missing_or_malformed_request_returns_422(api):
    assert post(api, {}, service_for()).status_code == 422
    with TestClient(api) as client:
        result = client.post("/api/v1/recommendation", content="{broken", headers={"Content-Type": "application/json"})
    assert result.status_code == 422


def test_original_budget_relaxation_metadata_and_counts_are_preserved(api):
    prop = property_result(sale_total_price_lkr=115)
    upstream = search([prop], total_found=50, relaxed_filters=True, warnings=["Expanded search"],
                      metadata={"dataset_size": 500, "top_n_requested": 30, "private_path": "C:/private"})
    service = service_for()
    service.search.return_value = upstream
    data = post(api, body(), service).json()
    assert data["status"] == "NO_SUITABLE_OPTION"
    assert data["alternatives"][0]["budget"]["budget_lkr"] == 100
    assert data["presentation"]["retrieval"]["relaxed_filters"]
    assert data["presentation"]["retrieval"]["metadata"] == {"dataset_size": 500, "top_n_requested": 30}
    assert "Expanded search" in data["warnings"]
    assert data["coverage"]["total_matching_candidates"] == 50
    assert data["coverage"]["retrieval_truncated"]
    assert data["coverage"]["retrieved_count"] == 1


def test_combined_partial_coverage_and_warnings(api):
    a, b = land("a"), land("b")
    evaluation = combined(option(a))
    evaluation.warnings = ["Only one assessed option"]
    service = service_for([a, b], combined_plan=Mock(return_value=evaluation))
    data = post(api, body(land_req()), service).json()
    assert data["coverage"]["planning_assessed_count"] == 1
    assert data["coverage"]["unassessed_ids"] == ["b"]
    assert data["coverage"]["planning_coverage_limited"]
    assert "Only one assessed option" in data["warnings"]


def test_no_candidates_skips_combined_planning(api):
    service = service_for()
    data = post(api, body(land_req()), service).json()
    assert data["status"] == "NO_SUITABLE_OPTION"
    service.combined_plan.assert_not_called()


@pytest.mark.parametrize("value", [RuntimeError("C:/private/path API-KEY-SECRET"), {"invalid": True}])
def test_retrieval_failures_and_invalid_responses_are_safe(api, value):
    service = service_for()
    if isinstance(value, Exception):
        service.search.side_effect = value
    else:
        service.search.return_value = value
    result = post(api, body(), service)
    assert result.status_code == 200
    assert result.json()["status"] == "INSUFFICIENT_EVIDENCE"
    assert "API-KEY-SECRET" not in result.text
    assert "C:/private" not in result.text


def test_combined_failure_retains_unassessed_candidates_and_never_retries(api):
    service = service_for([land()], combined_plan=Mock(side_effect=RuntimeError("secret")))
    data = post(api, body(land_req()), service).json()
    assert data["status"] == "INSUFFICIENT_EVIDENCE"
    assert data["coverage"]["unassessed_ids"] == ["a"]
    assert data["presentation"]["properties"][0]["listing_id"] == "a"
    assert service.combined_plan.call_count == 1
    service.direct_plan.assert_not_called()


def test_owned_planning_failure_is_insufficient_not_success(api):
    service = service_for(direct_plan=Mock(side_effect=RuntimeError("secret")))
    req = requirements(intent="PLAN_HOUSE", construction_budget_lkr=100, land_size_perches=10,
                       bedrooms=3, bathrooms=2, floors=1)
    result = post(api, body(req, owned_land={"land_width_ft": 50, "land_length_ft": 80}), service)
    assert result.status_code == 200
    assert result.json()["status"] == "INSUFFICIENT_EVIDENCE"
    assert result.json()["presentation"]["owned_plan"] is None


def test_explanation_disabled_never_constructs_provider(api):
    factory = Mock(side_effect=AssertionError("must not be called"))
    service = service_for([property_result()], explanation_factory=factory)
    data = post(api, body(explanation_enabled=False), service).json()
    assert data["explanation_status"] == "DETERMINISTIC"
    factory.assert_not_called()


def test_enabled_provider_failure_falls_back_without_changing_decisions(api):
    fake = FakeProvider(responses=[TimeoutError("private-key")])
    service = service_for([property_result()], explanation_factory=lambda: ExplanationService(fake))
    original = post(api, body(), service).json()
    result = post(api, body(explanation_enabled=True), service)
    assert result.status_code == 200
    data = result.json()
    assert data["explanation_status"] == "DETERMINISTIC_FALLBACK"
    assert data["recommendations"] == original["recommendations"]
    assert len(fake.calls) == 1
    assert "private-key" not in result.text


def test_enabled_valid_provider_returns_llm(api):
    service = service_for([property_result()], explanation_factory=lambda: ExplanationService(FakeProvider()))
    assert post(api, body(explanation_enabled=True), service).json()["explanation_status"] == "LLM"


def test_enabled_missing_provider_returns_fallback(api):
    assert post(api, body(explanation_enabled=True), service_for([property_result()])).json()["explanation_status"] == "DETERMINISTIC_FALLBACK"


def test_unexpected_internal_error_is_sanitized_500(api):
    service = Mock()
    service.run.side_effect = RuntimeError("C:/private/secret API-KEY")
    result = post(api, body(), service)
    assert result.status_code == 500
    assert result.json() == {"detail": "Recommendation processing failed. Please try again."}


def test_existing_combined_entry_point_is_called_directly_once(monkeypatch):
    from app.api.v1 import planning
    handler = Mock(return_value=combined())
    monkeypatch.setattr(planning, "evaluate_land_house", handler)
    request = object()
    assert module.existing_combined_evaluation(request).returned == 0
    handler.assert_called_once_with(request)


def test_real_combined_pipeline_keeps_ten_option_cap_without_double_planning(monkeypatch):
    from app.api.v1 import planning
    from app.schemas.planning import LandHouseEvaluationRequest
    generated = owned_response()
    generated.files.json = None
    generate = Mock(return_value=generated)
    monkeypatch.setattr(planning.HomePlanningAgent, "generate", generate)
    props = [land(str(i), sale_total_price_lkr=1_000_000) for i in range(12)]
    evaluation = module.existing_combined_evaluation(LandHouseEvaluationRequest(
        requirements=land_req(total_project_budget_lkr=50_000_000),
        property_results=[p.model_dump() for p in props]))
    assert evaluation.returned == 10
    assert generate.call_count == 10


def test_safe_artifact_projection_and_no_input_mutation(api, tmp_path):
    prop = land()
    opt = option(prop)
    source = str(presentation.PLANS_ROOT / "plan-example" / "floor_1.png")
    opt.planning.update(png_url=source, png_urls=[source],
                        json_url="C:/outside/secrets.json", budget_doc_url="https://evil.example",
                        internal_path="C:/private")
    evaluation = combined(opt)
    before = evaluation.model_dump()
    service = service_for([prop], combined_plan=Mock(return_value=evaluation))
    data = post(api, body(land_req()), service).json()
    plan = data["presentation"]["land_house_options"][0]["planning"]
    assert plan["png_url"] == "/plans/plan-example/floor_1.png"
    assert plan["json_url"] is None
    assert plan["budget_doc_url"] is None
    assert "internal_path" not in plan
    assert evaluation.model_dump() == before


@pytest.mark.parametrize("path", ["/plans/../secret.json", "/plans/plan-a/../../secret.json",
                                  "/plans/plan-a/%2e%2e%2fsecret.json", "//evil/plan-a/a.svg",
                                  "javascript:alert(1)", "/plans/plan-a/a.exe"])
def test_artifact_traversal_external_and_executable_paths_rejected(path):
    assert presentation.artifact_url(path) is None


def test_missing_budget_clarifies_without_upstream_work(api):
    service = service_for()
    data = post(api, body(requirements(maximum_budget_lkr=None)), service).json()
    assert data["status"] == "NEEDS_CLARIFICATION"
    service.search.assert_not_called()


@pytest.mark.parametrize("change", [{"maximum_budget_lkr": 10**400}, {"original_query": "   "}])
def test_malformed_requirement_extremes_return_422(api, change):
    payload = body()
    payload["requirements"].update(change)
    assert post(api, payload, service_for()).status_code == 422
