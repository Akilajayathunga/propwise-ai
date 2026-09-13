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

    inaccessible = _inaccessible_required_rooms(candidate, required_ids)
    if inaccessible:
        errors.append(f"Inaccessible rooms: {', '.join(sorted(inaccessible))}")

    if candidate.floors > 1:
        for floor in range(1, candidate.floors + 1):
            if not any(room.floor_number == floor and room.type in {"staircase", "hallway"} for room in candidate.rooms):
                errors.append(f"Floor {floor} has disconnected circulation.")

    if "master_bedroom" in present_ids and "bathroom_1" in present_ids:
        if "bathroom_1" not in candidate.access_graph.get("master_bedroom", []):
            errors.append("Master bathroom is not connected to the master bedroom.")

    if candidate.parking:
        parking_rect = Rect(candidate.parking.x, candidate.parking.y, candidate.parking.width, candidate.parking.height)
        footprint_on_site = candidate.footprint
        if rectangles_overlap(parking_rect, footprint_on_site):
            errors.append("Parking overlaps the building footprint.")
        if "entrance" not in candidate.access_graph.get("parking", []):
            errors.append("Parking is not connected to the entrance sequence.")

    for door in candidate.doors:
        if door.width <= 0:
            errors.append(f"Door {door.id} has invalid width.")
        if door.floor_number < 1 or door.floor_number > candidate.floors:
            errors.append(f"Door {door.id} has invalid floor.")
        if not (0 <= door.x <= candidate.footprint.width and 0 <= door.y <= candidate.footprint.height):
            errors.append(f"Door {door.id} is outside valid walls.")

    exterior_walls = {wall.id for wall in candidate.walls if wall.wall_type == "exterior"}
    for window in candidate.windows:
        if window.wall not in exterior_walls:
            errors.append(f"Window {window.id} is not on an external wall.")

    if candidate.site.exact_site_fit_verified:
        if not inside(candidate.footprint, candidate.site.conceptual_envelope):
            errors.append("Building footprint is outside the verified site boundary.")

    return not errors, errors


def _inaccessible_required_rooms(candidate: CandidatePlan, required_ids: set[str]) -> set[str]:
    start = "entrance" if "entrance" in candidate.access_graph else next(iter(candidate.access_graph), "")
    if not start:
        return required_ids
    visited = set()
    stack = [start]
    while stack:
        node = stack.pop()
        if node in visited:
            continue
        visited.add(node)
        for neighbor in candidate.access_graph.get(node, []):
            if neighbor not in visited:
                stack.append(neighbor)
    return {room_id for room_id in required_ids if room_id not in visited}
