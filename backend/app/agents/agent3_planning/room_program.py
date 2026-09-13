import json
from pathlib import Path

from app.agents.agent3_planning.models import RoomRequirement
from app.schemas.planning import PlanningRequest

ROOT = Path(__file__).resolve().parents[4]
ROOM_SIZES_PATH = ROOT / "data" / "knowledge" / "room_sizes.json"


def load_room_sizes() -> dict:
    with ROOM_SIZES_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _room(room_id: str, room_type: str, label: str, required: bool, priority: int, floor: int | None, sizes: dict) -> RoomRequirement:
    info = sizes[room_type]
    return RoomRequirement(
        id=room_id,
        type=room_type,
        label=label,
        required=required,
        priority=priority,
        preferred_area=float(info["preferred_area_sqft"]),
        minimum_area=float(info["minimum_area_sqft"]),
        floor_preference=floor,
    )


def build_room_program(request: PlanningRequest) -> list[RoomRequirement]:
    sizes = load_room_sizes()
    bedrooms = request.bedrooms or 3
    bathrooms = request.bathrooms or max(1, min(bedrooms, 2))
    floors = request.floors or 1
    rooms = [
        _room("entrance", "entrance", "Entrance", True, 10, 1, sizes),
        _room("living", "living_room", "Living Room", True, 10, 1, sizes),
        _room("dining", "dining", "Dining", True, 8, 1, sizes),
        _room("kitchen", "kitchen", "Kitchen", True, 9, 1, sizes),
        _room("master_bedroom", "master_bedroom", "Master Bedroom", True, 10, floors, sizes),
    ]

    for index in range(1, bedrooms):
        preferred_floor = floors if floors > 1 else 1
        rooms.append(_room(f"bedroom_{index}", "bedroom", f"Bedroom {index + 1}", True, 8, preferred_floor, sizes))

    for index in range(bathrooms):
        if index == 0:
            preferred_floor = floors
        elif index == 1:
            preferred_floor = 1
        else:
            preferred_floor = floors if floors > 1 else 1
        label = "Master Bathroom" if index == 0 else f"Bathroom {index + 1}"
        rooms.append(_room(f"bathroom_{index + 1}", "bathroom", label, True, 8, preferred_floor, sizes))

    if floors > 1:
        rooms.append(_room("stairs", "staircase", "Staircase", True, 10, 1, sizes))
    if request.office_required:
        rooms.append(_room("office", "office", "Office", False, 7, 1, sizes))
    if request.family_lounge_required:
        rooms.append(_room("family_lounge", "family_lounge", "Family Lounge", False, 7, floors, sizes))
    if request.utility_room_required:
        rooms.append(_room("utility", "utility", "Utility", False, 6, 1, sizes))
    if request.balcony_required:
        rooms.append(_room("balcony", "balcony", "Balcony", False, 4, floors, sizes))
    if request.parking_spaces:
        rooms.append(_room("parking", "parking", "Parking", True, 8, 1, sizes))

    return rooms
