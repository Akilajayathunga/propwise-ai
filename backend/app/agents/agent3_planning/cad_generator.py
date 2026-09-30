from pathlib import Path

import ezdxf

from app.agents.agent3_planning.models import CandidatePlan, Rect


LAYERS = [
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
]


def generate_dxf(plan: CandidatePlan, output_dir: Path) -> str:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "propwise_plan.dxf"
    doc = ezdxf.new("R2010")
    for layer in LAYERS:
        if layer not in doc.layers:
            doc.layers.add(layer)
    msp = doc.modelspace()

    _rect(msp, 0, 0, plan.site.conceptual_envelope.width, plan.site.conceptual_envelope.height, "LAND_BOUNDARY")
    x_offset = 0.0
    for floor in range(1, plan.floors + 1):
        _rect(msp, x_offset, 0, plan.footprint.width, plan.footprint.height, "EXTERIOR_WALLS")
        msp.add_text("GROUND FLOOR" if floor == 1 else f"FLOOR {floor}", dxfattribs={"height": 1.8, "layer": "ANNOTATIONS"}).set_placement((x_offset, -4))

        for room in [room for room in plan.rooms if room.floor_number == floor]:
            layer = "STAIRS" if room.type == "staircase" else "INTERIOR_WALLS"
            _rect(msp, x_offset + room.x, room.y, room.width, room.height, layer)
            msp.add_text(room.label.upper(), dxfattribs={"height": 1.1, "layer": "ROOM_LABELS"}).set_placement((x_offset + room.x + 1, room.y + room.height / 2))

        for door in [door for door in plan.doors if door.floor_number == floor]:
            _door(msp, x_offset + door.x, door.y, door.width, door.orientation)
        for window in [window for window in plan.windows if window.floor_number == floor]:
            _window(msp, x_offset + window.x, window.y, window.width, window.orientation)
        for fixture in [fixture for fixture in plan.fixtures if fixture.floor_number == floor and fixture.room_id != "parking"]:
            _rect(msp, x_offset + fixture.x, fixture.y, fixture.width, fixture.height, "FIXTURES")
        for dimension in [dimension for dimension in plan.dimensions if dimension.floor_number == floor and dimension.dimension_type == "overall"]:
            msp.add_line((x_offset + dimension.x1, dimension.y1 + dimension.offset), (x_offset + dimension.x2, dimension.y2 + dimension.offset), dxfattribs={"layer": "DIMENSIONS"})
            msp.add_text(dimension.label, dxfattribs={"height": 0.9, "layer": "DIMENSIONS"}).set_placement((x_offset + (dimension.x1 + dimension.x2) / 2, (dimension.y1 + dimension.y2) / 2 + dimension.offset))

        x_offset += plan.footprint.width + 24

    if plan.parking:
        _rect(msp, plan.parking.x, plan.parking.y, plan.parking.width, plan.parking.height, "PARKING")
        for index in range(plan.parking.spaces):
            _rect(msp, plan.parking.x + index * 10 + 0.8, plan.parking.y + 1, 8.4, 13.5, "PARKING")
            msp.add_text(f"CAR {index + 1}", dxfattribs={"height": 0.9, "layer": "PARKING"}).set_placement((plan.parking.x + index * 10 + 2.0, plan.parking.y + 7))

    msp.add_text("Conceptual AI-assisted plan only. Not construction CAD.", dxfattribs={"height": 2, "layer": "ANNOTATIONS"}).set_placement((0, -10))
    doc.saveas(path)
    return str(path)


def _rect(msp, x: float, y: float, width: float, height: float, layer: str) -> None:
    points = [(x, y), (x + width, y), (x + width, y + height), (x, y + height), (x, y)]
    msp.add_lwpolyline(points, dxfattribs={"layer": layer})


def _door(msp, x: float, y: float, width: float, orientation: str) -> None:
    if orientation == "vertical":
        msp.add_line((x, y - width / 2), (x, y + width / 2), dxfattribs={"layer": "DOORS"})
        msp.add_arc((x, y), width, 0, 90, dxfattribs={"layer": "DOORS"})
    else:
        msp.add_line((x - width / 2, y), (x + width / 2, y), dxfattribs={"layer": "DOORS"})
        msp.add_arc((x, y), width, 270, 360, dxfattribs={"layer": "DOORS"})


def _window(msp, x: float, y: float, width: float, orientation: str) -> None:
    if orientation == "vertical":
        msp.add_line((x, y - width / 2), (x, y + width / 2), dxfattribs={"layer": "WINDOWS"})
    else:
        msp.add_line((x - width / 2, y), (x + width / 2, y), dxfattribs={"layer": "WINDOWS"})
