from app.agents.agent3_planning.geometry import inside, rectangles_overlap, room_rect
from app.agents.agent3_planning.models import CandidatePlan, Rect, RoomRequirement


def validate_candidate(candidate: CandidatePlan, program: list[RoomRequirement]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    required_ids = {room.id for room in program if room.required and room.type != "parking"}
    present_ids = {room.id for room in candidate.rooms}
    missing = sorted(required_ids - present_ids)
    if missing:
        errors.append(f"Required rooms missing: {', '.join(missing)}")

    for room in candidate.rooms:
        if room.width <= 0 or room.height <= 0:
            errors.append(f"Room {room.id} has non-positive dimensions.")
        if not inside(room_rect(room), Rect(0, 0, candidate.footprint.width, candidate.footprint.height)):
            errors.append(f"Room {room.id} is outside the building footprint.")

    for idx, room in enumerate(candidate.rooms):
        for other in candidate.rooms[idx + 1 :]:
            if room.floor_number == other.floor_number and rectangles_overlap(room_rect(room), room_rect(other)):
                errors.append(f"Rooms {room.id} and {other.id} overlap.")

    if candidate.floors > 1 and not any(room.type == "staircase" for room in candidate.rooms):
        errors.append("Staircase is required for multi-storey layouts.")

    if candidate.parking:
        parking_rect = Rect(candidate.parking.x, candidate.parking.y, candidate.parking.width, candidate.parking.height)
        footprint_on_site = candidate.footprint
        if rectangles_overlap(parking_rect, footprint_on_site):
            errors.append("Parking overlaps the building footprint.")

    if candidate.site.exact_site_fit_verified:
        if not inside(candidate.footprint, candidate.site.conceptual_envelope):
            errors.append("Building footprint is outside the verified site boundary.")

    return not errors, errors

