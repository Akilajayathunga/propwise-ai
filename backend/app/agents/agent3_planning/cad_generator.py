from pathlib import Path

import ezdxf

from app.agents.agent3_planning.models import CandidatePlan


def generate_dxf(plan: CandidatePlan, output_dir: Path) -> str:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "propwise_plan.dxf"
    doc = ezdxf.new("R2010")
    for layer in ["LAND_BOUNDARY", "WALLS", "DOORS", "WINDOWS", "ROOM_LABELS", "DIMENSIONS", "STAIRS", "PARKING", "ANNOTATIONS"]:
        doc.layers.add(layer)
    msp = doc.modelspace()
    _rect(msp, 0, 0, plan.site.conceptual_envelope.width, plan.site.conceptual_envelope.height, "LAND_BOUNDARY")
    _rect(msp, plan.footprint.x, plan.footprint.y, plan.footprint.width, plan.footprint.height, "WALLS")
    x_offset = 0
    for floor in range(1, plan.floors + 1):
        for room in [room for room in plan.rooms if room.floor_number == floor]:
            x = plan.footprint.x + room.x + x_offset
            y = plan.footprint.y + room.y
            _rect(msp, x, y, room.width, room.height, "WALLS")
            msp.add_text(room.label, dxfattribs={"height": 1.5, "layer": "ROOM_LABELS"}).set_placement((x + 1, y + 1))
        x_offset += plan.footprint.width + 20
    if plan.parking:
        _rect(msp, plan.parking.x, plan.parking.y, plan.parking.width, plan.parking.height, "PARKING")
    msp.add_text("Conceptual AI-assisted plan only. Not construction CAD.", dxfattribs={"height": 2, "layer": "ANNOTATIONS"}).set_placement((0, -8))
    doc.saveas(path)
    return str(path)


def _rect(msp, x: float, y: float, width: float, height: float, layer: str) -> None:
    points = [(x, y), (x + width, y), (x + width, y + height), (x, y + height), (x, y)]
    msp.add_lwpolyline(points, dxfattribs={"layer": layer})

