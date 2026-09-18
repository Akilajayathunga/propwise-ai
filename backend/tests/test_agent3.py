import json
from pathlib import Path

import ezdxf

from app.agents.agent3_planning.agent import HomePlanningAgent
from app.agents.agent3_planning.candidate_generator import generate_candidates
from app.agents.agent3_planning.constraints import validate_candidate
from app.agents.agent3_planning.models import CandidatePlan, Parking, Rect, Room, SiteAnalysis
from app.agents.agent3_planning.optimizer import select_best_candidate
from app.agents.agent3_planning.property_adapter import adapt_selected_property
from app.agents.agent3_planning.room_program import build_room_program
from app.agents.agent3_planning.site_analyzer import analyze_site
from app.schemas.planning import PlanningRequest
from app.schemas.requirements import Intent

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "agent2_land_result.json"


def load_agent2_land_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def plan_house_request(**overrides) -> PlanningRequest:
    data = {
        "intent": Intent.PLAN_HOUSE,
        "location": "Malabe",
        "land_size_perches": 15,
        "bedrooms": 4,
        "bathrooms": 3,
        "floors": 2,
        "parking_spaces": 2,
        "office_required": True,
        "balcony_required": True,
        "candidate_count": 6,
    }
    data.update(overrides)
    return PlanningRequest(**data)


def test_agent2_result_to_property_adapter() -> None:
    selected = adapt_selected_property(load_agent2_land_fixture())

    assert selected is not None
    assert selected.listing_id == "land-kottawa-001"
    assert selected.location == "Kottawa"
    assert selected.district == "Colombo"
    assert selected.property_type == "land"


def test_sale_total_price_maps_to_land_price() -> None:
    selected = adapt_selected_property(load_agent2_land_fixture())

    assert selected is not None
    assert selected.land_price_lkr == 13_000_000
    assert selected.source_score == 0.88


def test_plan_house_without_agent2() -> None:
    response = HomePlanningAgent().generate(plan_house_request(candidate_count=3))

    assert response.constraints_satisfied
    assert response.selected_property is None
    assert response.plan is not None
    assert response.estimated_floor_area_sqft and response.estimated_floor_area_sqft > 0


def test_land_and_house_using_agent2_style_result() -> None:
    response = HomePlanningAgent().generate(
        PlanningRequest(
            intent=Intent.LAND_AND_HOUSE,
            selected_property=load_agent2_land_fixture(),
            total_project_budget_lkr=40_000_000,
            bedrooms=3,
            bathrooms=2,
            floors=2,
            parking_spaces=1,
            candidate_count=3,
        )
    )

    assert response.constraints_satisfied
    assert response.selected_property is not None
    assert response.selected_property.land_price_lkr == 13_000_000
    assert response.remaining_construction_budget_lkr == 27_000_000


def test_remaining_construction_budget_calculation() -> None:
    selected = adapt_selected_property(load_agent2_land_fixture())
    request = PlanningRequest(
        intent=Intent.LAND_AND_HOUSE,
        selected_property=selected,
        total_project_budget_lkr=40_000_000,
        bedrooms=3,
        bathrooms=2,
        floors=2,
    )
    response = HomePlanningAgent().generate(request)

    assert response.remaining_construction_budget_lkr == 27_000_000


def test_missing_land_dimensions_warning_and_no_invention() -> None:
    response = HomePlanningAgent().generate(plan_house_request(candidate_count=2))

    assert response.exact_site_fit_verified is False
    assert any("exact plot dimensions are unavailable" in warning for warning in response.warnings)
    assert response.plan is not None
    assert response.plan["site"]["width_ft"] is None
    assert response.plan["site"]["length_ft"] is None


def test_room_program_contains_requested_rooms() -> None:
    program = build_room_program(plan_house_request())

    assert any(room.type == "living_room" for room in program)
    assert any(room.type == "kitchen" for room in program)
    assert any(room.type == "office" for room in program)
    assert any(room.type == "balcony" for room in program)


def test_correct_bedroom_and_bathroom_count() -> None:
    program = build_room_program(plan_house_request(bedrooms=4, bathrooms=3))

    bedroom_count = len([room for room in program if room.type in {"master_bedroom", "bedroom"}])
    bathroom_count = len([room for room in program if room.type == "bathroom"])
    assert bedroom_count == 4
    assert bathroom_count == 3


def test_staircase_exists_for_multi_storey() -> None:
    program = build_room_program(plan_house_request(floors=2))

    assert any(room.type == "staircase" for room in program)


def test_multiple_candidates_are_generated() -> None:
    request = plan_house_request(candidate_count=5)
    site = analyze_site(request, None)
    program = build_room_program(request)
    candidates = generate_candidates(request, site, program, count=5)

    assert len(candidates) == 5
    footprints = {(candidate.footprint.x, candidate.footprint.y, candidate.footprint.width) for candidate in candidates}
    assert len(footprints) > 1


def test_overlapping_candidates_are_rejected() -> None:
    site = SiteAnalysis(None, None, 60, 80, True, Rect(0, 0, 60, 80))
    candidate = CandidatePlan(
        "bad",
        site,
        Rect(0, 0, 30, 30),
        1,
        [
            Room("living", "living_room", "Living", 1, 0, 0, 20, 20, 400),
            Room("dining", "dining", "Dining", 1, 10, 10, 20, 20, 400),
        ],
        None,
    )
    program = [
        build_room_program(plan_house_request(bedrooms=1, bathrooms=1, floors=1))[0],
    ]

    valid, errors = validate_candidate(candidate, program)
    assert not valid
    assert any("overlap" in error for error in errors)


def test_positive_room_dimensions_and_inside_footprint() -> None:
    response = HomePlanningAgent().generate(plan_house_request(candidate_count=3))

    assert response.plan is not None
    footprint = response.plan["building_footprint"]
    for room in response.plan["rooms"]:
        assert room["width"] > 0
        assert room["height"] > 0
        assert room["x"] + room["width"] <= footprint["width"]
        assert room["y"] + room["height"] <= footprint["height"]


def test_parking_does_not_overlap_building() -> None:
    response = HomePlanningAgent().generate(plan_house_request(candidate_count=3))

    assert response.plan is not None
    assert response.plan["parking"] is not None
    assert response.constraints_satisfied


def test_valid_candidate_scoring_and_highest_selected() -> None:
    request = plan_house_request(candidate_count=5)
    site = analyze_site(request, None)
    program = build_room_program(request)
    candidates = generate_candidates(request, site, program, count=5)
    best, valid, _ = select_best_candidate(candidates, program)

    assert best is not None
    assert valid
    assert best.score == max(candidate.score for candidate in valid)
    assert "requirement_satisfaction" in best.score_breakdown


def test_graceful_all_candidates_invalid_response() -> None:
    response = HomePlanningAgent().generate(
        PlanningRequest(
            intent=Intent.PLAN_HOUSE,
            land_width_ft=8,
            land_length_ft=8,
            bedrooms=20,
            bathrooms=20,
            floors=1,
            candidate_count=2,
        )
    )

    assert response.constraints_satisfied is False
    assert response.suggestions


def test_canonical_json_svg_png_and_dxf_generated() -> None:
    response = HomePlanningAgent().generate(plan_house_request(candidate_count=3))

    assert response.plan is not None
    assert response.files.json and Path(response.files.json).exists()
    assert response.files.svg and all(Path(path).exists() for path in response.files.svg)
    assert response.files.png and all(Path(path).exists() for path in response.files.png)
    assert response.files.dxf and Path(response.files.dxf).exists()


def test_dxf_can_be_reopened() -> None:
    response = HomePlanningAgent().generate(plan_house_request(candidate_count=2))

    assert response.files.dxf is not None
    doc = ezdxf.readfile(response.files.dxf)
    assert doc.modelspace() is not None


def test_configured_construction_costs_are_available() -> None:
    response = HomePlanningAgent().generate(plan_house_request(candidate_count=2))

    assert response.budget_estimation_available is True
    assert response.construction_cost_estimate is not None
    assert response.construction_cost_estimate["profile"] == "standard"
    assert response.construction_cost_estimate["expected_lkr"] > 0


def test_circulation_connects_required_rooms() -> None:
    response = HomePlanningAgent().generate(plan_house_request(candidate_count=4))

    assert response.plan is not None
    graph = response.plan["access_graph"]
    required_room_ids = {room["id"] for room in response.plan["rooms"] if room["zone"] != "external"}
    visited = set()
    stack = ["entrance"]
    while stack:
        node = stack.pop()
        if node in visited:
            continue
        visited.add(node)
        stack.extend(graph.get(node, []))

    assert required_room_ids <= visited
    assert "hall_ground" in graph


def test_master_bathroom_connected_to_master_bedroom() -> None:
    response = HomePlanningAgent().generate(plan_house_request(candidate_count=4))

    assert response.plan is not None
    assert "bathroom_1" in response.plan["access_graph"]["master_bedroom"]


def test_doors_have_valid_positions() -> None:
    response = HomePlanningAgent().generate(plan_house_request(candidate_count=4))

    assert response.plan is not None
    footprint = response.plan["building_footprint"]
    assert response.plan["doors"]
    for door in response.plan["doors"]:
        assert door["width"] > 0
        assert 0 <= door["x"] <= footprint["width"]
        assert 0 <= door["y"] <= footprint["height"]


def test_windows_are_only_on_external_walls() -> None:
    response = HomePlanningAgent().generate(plan_house_request(candidate_count=4))

    assert response.plan is not None
    exterior_walls = {wall["id"] for wall in response.plan["walls"] if wall["wall_type"] == "exterior"}
    assert response.plan["windows"]
    assert all(window["wall"] in exterior_walls for window in response.plan["windows"])


def test_parking_has_entrance_relationship() -> None:
    response = HomePlanningAgent().generate(plan_house_request(candidate_count=4))

    assert response.plan is not None
    assert response.plan["parking"] is not None
    assert "entrance" in response.plan["access_graph"]["parking"]


def test_space_efficiency_metrics_exist() -> None:
    response = HomePlanningAgent().generate(plan_house_request(candidate_count=4))

    assert response.plan is not None
    metrics = response.plan["space_metrics"]
    assert metrics["usable_room_area"] > 0
    assert metrics["circulation_area"] > 0
    assert metrics["footprint_area"] > metrics["usable_room_area"]
    assert 0 <= metrics["space_efficiency_score"] <= 100


def test_wall_generation_includes_exterior_and_interior() -> None:
    response = HomePlanningAgent().generate(plan_house_request(candidate_count=4))

    assert response.plan is not None
    wall_types = {wall["wall_type"] for wall in response.plan["walls"]}
    assert {"exterior", "interior"} <= wall_types


def test_svg_contains_architectural_symbols() -> None:
    response = HomePlanningAgent().generate(plan_house_request(candidate_count=4))

    assert response.files.svg
    svg_text = Path(response.files.svg[0]).read_text(encoding="utf-8")
    assert 'class="door"' in svg_text
    assert 'class="window"' in svg_text
    assert 'class="stairs"' in svg_text
    assert 'class="dimension"' in svg_text
    assert "Conceptual AI-assisted plan" in svg_text


def test_fixture_symbols_are_in_canonical_json() -> None:
    response = HomePlanningAgent().generate(plan_house_request(candidate_count=4))

    assert response.plan is not None
    fixture_types = {fixture["fixture_type"] for fixture in response.plan["fixtures"]}
    assert {"bed", "sofa", "dining_table", "counter", "wc", "stair_treads", "vehicle"} <= fixture_types


def test_dxf_architectural_layers_exist() -> None:
    response = HomePlanningAgent().generate(plan_house_request(candidate_count=4))

    assert response.files.dxf is not None
    doc = ezdxf.readfile(response.files.dxf)
    layer_names = {layer.dxf.name for layer in doc.layers}
    assert {
        "LAND_BOUNDARY",
        "EXTERIOR_WALLS",
        "INTERIOR_WALLS",
        "DOORS",
        "WINDOWS",
        "ROOM_LABELS",
        "DIMENSIONS",
        "STAIRS",
        "PARKING",
        "FIXTURES",
        "ANNOTATIONS",
    } <= layer_names


def test_canonical_json_contains_renderer_geometry() -> None:
    response = HomePlanningAgent().generate(plan_house_request(candidate_count=4))

    assert response.plan is not None
    assert response.plan["zones"]
    assert response.plan["walls"]
    assert response.plan["doors"]
    assert response.plan["windows"]
    assert response.plan["fixtures"]
    assert response.plan["dimensions"]
    assert response.plan["conceptual_notice"] == "Conceptual AI-assisted plan only. Not construction-ready."
