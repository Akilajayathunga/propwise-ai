import math
import random

from app.agents.agent3_planning.floor_allocator import allocate_floors
from app.agents.agent3_planning.models import CandidatePlan, Parking, Rect, Room, RoomRequirement, SiteAnalysis
from app.schemas.planning import PlanningRequest


def _room_dimensions(area: float, variant: int) -> tuple[float, float]:
    ratio = [1.0, 1.2, 0.85, 1.35][variant % 4]
    width = max(8.0, math.sqrt(area * ratio))
    height = max(8.0, area / width)
    return round(width, 2), round(height, 2)


def _pack_rooms(rooms: list[RoomRequirement], floor: int, footprint: Rect, variant: int) -> list[Room]:
    ordered = sorted(rooms, key=lambda item: (-item.priority, item.id))
    if variant % 2:
        ordered = list(reversed(ordered))

    placed: list[Room] = []
    cursor_x = footprint.x
    cursor_y = footprint.y
    row_height = 0.0
    gap = 2.0

    for index, room in enumerate(ordered):
        if room.type == "parking":
            continue
        width, height = _room_dimensions(room.preferred_area, variant + index)
        if cursor_x + width > footprint.right:
            cursor_x = footprint.x
            cursor_y += row_height + gap
            row_height = 0.0
        placed.append(Room(room.id, room.type, room.label, floor, cursor_x, cursor_y, width, height, round(width * height, 2)))
        cursor_x += width + gap
        row_height = max(row_height, height)
    return placed


def generate_candidates(
    request: PlanningRequest,
    site: SiteAnalysis,
    program: list[RoomRequirement],
    count: int,
    seed: int = 42,
) -> list[CandidatePlan]:
    rng = random.Random(seed)
    floors = request.floors or 1
    allocation = allocate_floors(program, floors)
    site_rect = site.conceptual_envelope
    setback = 5.0
    max_width = site_rect.width - setback * 2
    max_length = site_rect.height - setback * 2
    total_area = sum(room.preferred_area for room in program if room.type != "parking")
    target_floor_area = max(450.0, total_area / floors * 1.8)

    candidates: list[CandidatePlan] = []
    for idx in range(count):
        if max_width < 18.0 or max_length < 18.0:
            width = max_width
            length = max_length
        else:
            width_factor = 0.90 + (idx % 3) * 0.03
            length_factor = 0.90 + (idx % 4) * 0.025
            width = max_width * min(width_factor, 0.98)
            length = max_length * min(length_factor, 0.98)
        jitter_x = rng.uniform(0, max(0.0, max_width - width))
        jitter_y = rng.uniform(0, max(0.0, max_length - length))
        footprint = Rect(site_rect.x + setback + jitter_x, site_rect.y + setback + jitter_y, round(width, 2), round(length, 2))

        rooms: list[Room] = []
        for floor in range(1, floors + 1):
            rooms.extend(_pack_rooms(allocation[floor], floor, Rect(0, 0, footprint.width, footprint.height), idx))

        parking = None
        if request.parking_spaces:
            parking_width = 10.0 * request.parking_spaces
            parking = Parking(
                spaces=request.parking_spaces,
                x=footprint.x,
                y=footprint.top + 3.0,
                width=parking_width,
                height=15.0,
            )

        candidates.append(CandidatePlan(f"candidate-{idx + 1}", site, footprint, floors, rooms, parking))
    return candidates
