import json
import uuid
import zipfile
from pathlib import Path

from app.agents.agent3_planning.budget import analyze_budget
from app.agents.agent3_planning.cad_generator import generate_dxf
from app.agents.agent3_planning.candidate_generator import generate_candidates
from app.agents.agent3_planning.optimizer import select_best_candidate
from app.agents.agent3_planning.property_adapter import adapt_selected_property
from app.agents.agent3_planning.renderer_png import render_png
from app.agents.agent3_planning.renderer_svg import render_svg
from app.agents.agent3_planning.room_program import build_room_program
from app.agents.agent3_planning.site_analyzer import analyze_site
from app.schemas.planning import PlanFileSet, PlanningRequest, PlanningResponse

ROOT = Path(__file__).resolve().parents[4]
STORAGE_ROOT = ROOT / "storage" / "plans"
DISCLAIMER = (
    "PropWise AI provides AI-assisted conceptual planning and preliminary decision-support information only. "
    "Generated layouts are not approved architectural, structural, engineering, quantity-surveying, legal, "
    "planning or construction documents. Final design, costs, site suitability, approvals and regulatory "
    "compliance must be verified by appropriately qualified professionals and relevant authorities."
)


class HomePlanningAgent:
    def generate(self, request: PlanningRequest) -> PlanningResponse:
        selected = adapt_selected_property(request.selected_property)
        if selected:
            request.location = request.location or selected.location
            request.land_size_perches = request.land_size_perches or selected.land_size_perches
            request.land_width_ft = request.land_width_ft or selected.land_width_ft
            request.land_length_ft = request.land_length_ft or selected.land_length_ft
            request.road_side = request.road_side or selected.road_side

        plan_id = f"plan-{uuid.uuid4().hex[:12]}"
        site = analyze_site(request, selected)
        program = build_room_program(request)
        candidates = generate_candidates(request, site, program, request.candidate_count)
        best, valid_candidates, rejection_reasons = select_best_candidate(candidates, program)

        if best is None:
            return PlanningResponse(
                plan_id=plan_id,
                constraints_satisfied=False,
                exact_site_fit_verified=site.exact_site_fit_verified,
                selected_property=selected,
                warnings=site.warnings + rejection_reasons,
                suggestions=[
                    "Reduce optional rooms.",
                    "Reduce room sizes.",
                    "Increase number of floors.",
                    "Provide exact land dimensions.",
                    "Increase available site size.",
                ],
                disclaimer=DISCLAIMER,
            )

        best.plan_id = plan_id
        estimated_area = round(sum(room.area_sqft for room in best.rooms), 2)
        output_dir = STORAGE_ROOT / plan_id
        plan_dict = canonical_plan(best, site.warnings)
        output_dir.mkdir(parents=True, exist_ok=True)
        json_path = output_dir / "plan.json"
        summary_path = output_dir / "summary.json"
        json_path.write_text(json.dumps(plan_dict, indent=2), encoding="utf-8")
        svg_paths = render_svg(best, output_dir)
        png_paths = render_png(best, output_dir)
        dxf_path = generate_dxf(best, output_dir)
        zip_path = _write_plan_zip(output_dir, png_paths, svg_paths, json_path)
        budget = analyze_budget(request, selected, estimated_area)

        summary = {
            "plan_id": plan_id,
            "estimated_floor_area_sqft": estimated_area,
            "layout_score": best.score,
            "budget_status": budget["budget_status"],
            "warnings": site.warnings,
            "disclaimer": DISCLAIMER,
        }
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

        return PlanningResponse(
            plan_id=plan_id,
            constraints_satisfied=True,
            exact_site_fit_verified=site.exact_site_fit_verified,
            selected_property=selected,
            estimated_floor_area_sqft=estimated_area,
            layout_score=best.score,
            score_breakdown=best.score_breakdown,
            remaining_construction_budget_lkr=budget["remaining_construction_budget_lkr"],
            budget_estimation_available=budget["budget_estimation_available"],
            budget_status=budget["budget_status"],
            floor_area_estimate=budget.get("floor_area_estimate"),
            construction_cost_estimate=budget.get("construction_cost_estimate"),
            total_project_estimate=budget.get("total_project_estimate"),
            assumptions=budget.get("assumptions", []),
            cost_disclaimer=budget.get("cost_disclaimer"),
            warnings=site.warnings,
            plan=plan_dict,
            files=PlanFileSet(json=str(json_path), svg=svg_paths, png=png_paths, dxf=str(dxf_path), zip=str(zip_path), summary=str(summary_path)),
            disclaimer=DISCLAIMER,
        )


def canonical_plan(plan, warnings: list[str]) -> dict:
    return {
        "plan_id": plan.plan_id,
        "units": "feet",
        "conceptual_notice": "Conceptual AI-assisted plan only. Not construction-ready.",
        "wall_parameters": {
            "exterior_wall_thickness": plan.exterior_wall_thickness,
            "interior_wall_thickness": plan.interior_wall_thickness,
        },
        "site": {
            "land_size_perches": plan.site.land_size_perches,
            "total_site_area_sqft": plan.site.total_site_area_sqft,
            "width_ft": plan.site.width_ft,
            "length_ft": plan.site.length_ft,
            "exact_site_fit_verified": plan.site.exact_site_fit_verified,
            "conceptual_envelope": plan.site.conceptual_envelope.__dict__,
        },
        "building_footprint": plan.footprint.__dict__,
        "zones": plan.zones,
        "floors": [{"floor_number": floor, "name": "Ground" if floor == 1 else f"Floor {floor}"} for floor in range(1, plan.floors + 1)],
        "rooms": [room.__dict__ for room in plan.rooms],
        "walls": [wall.__dict__ for wall in plan.walls],
        "doors": [door.__dict__ for door in plan.doors],
        "windows": [window.__dict__ for window in plan.windows],
        "circulation": plan.circulation,
        "access_graph": plan.access_graph,
        "stairs": [room.__dict__ for room in plan.rooms if room.type == "staircase"],
        "parking": plan.parking.__dict__ if plan.parking else None,
        "fixtures": [fixture.__dict__ for fixture in plan.fixtures],
        "dimensions": [dimension.__dict__ for dimension in plan.dimensions],
        "space_metrics": plan.space_metrics,
        "warnings": warnings,
        "score": plan.score,
        "score_breakdown": plan.score_breakdown,
    }


def _write_plan_zip(output_dir: Path, png_paths: list[str], svg_paths: list[str], json_path: Path) -> Path:
    zip_path = output_dir / "all_floor_plans.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path_value in png_paths:
            path = Path(path_value)
            if path.exists():
                archive.write(path, arcname=path.name)
        for path_value in svg_paths:
            path = Path(path_value)
            if path.exists():
                archive.write(path, arcname=path.name)
        if json_path.exists():
            archive.write(json_path, arcname=json_path.name)
    return zip_path
