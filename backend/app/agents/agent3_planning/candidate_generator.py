import math
import random

from app.agents.agent3_planning.floor_allocator import allocate_floors
from app.agents.agent3_planning.models import (
    CandidatePlan,
    Dimension,
    Door,
    Fixture,
    Parking,
    Rect,
    Room,
    RoomRequirement,
    SiteAnalysis,
    Wall,
    Window,
)
from app.schemas.planning import PlanningRequest


ZONE_BY_TYPE = {
    "entrance": "public",
    "living_room": "public",
    "dining": "public",
    "kitchen": "service",
    "utility": "service",
    "bathroom": "service",
    "master_bedroom": "private",
    "bedroom": "private",
    "family_lounge": "private",
    "office": "private",
    "staircase": "circulation",
    "hallway": "circulation",
    "balcony": "external",
}

EXTERIOR_WALL_THICKNESS = 0.75
INTERIOR_WALL_THICKNESS = 0.35


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
    allocated_preferred_by_floor = {
        floor: sum(room.preferred_area for room in allocation[floor] if room.type != "parking") for floor in range(1, floors + 1)
    }

    candidates: list[CandidatePlan] = []
    for idx in range(count):
        minimum_floor_area = 2200.0 if floors > 1 else 1350.0
        target_area_per_floor = max(minimum_floor_area, max(allocated_preferred_by_floor.values()) / 0.66)
        ratio = [1.12, 1.28, 0.96, 1.38, 1.05][idx % 5]
        width = max(28.0, math.sqrt(target_area_per_floor * ratio))
        length = max(32.0, target_area_per_floor / width)

        max_width = max(18.0, site_rect.width - 10.0)
        max_length = max(18.0, site_rect.height - 10.0)
        if width > max_width:
            width = max_width
            length = target_area_per_floor / width
        if length > max_length:
            length = max_length
            width = target_area_per_floor / length

        width = min(width + (idx % 3) * 2.0, max_width)
        length = min(length + (idx % 4) * 1.5, max_length)
        footprint = _place_footprint(site_rect, round(width, 2), round(length, 2), idx, rng)

        rooms: list[Room] = []
        for floor in range(1, floors + 1):
            floor_rooms = _rooms_for_floor(allocation[floor], floor, footprint, floors, idx)
            rooms.extend(floor_rooms)

        parking = _parking_for_request(request, footprint)
        plan = CandidatePlan(f"candidate-{idx + 1}", site, footprint, floors, rooms, parking)
        _enrich_architectural_geometry(plan)
        candidates.append(plan)
    return candidates


def _place_footprint(site: Rect, width: float, length: float, idx: int, rng: random.Random) -> Rect:
    setback = 5.0
    usable_width = max(0.0, site.width - width - setback * 2)
    usable_length = max(0.0, site.height - length - setback * 2)
    x_bias = [0.15, 0.5, 0.82, 0.35][idx % 4]
    y_bias = [0.18, 0.12, 0.25, 0.2][idx % 4]
    x = site.x + setback + usable_width * x_bias + rng.uniform(-1.0, 1.0)
    y = site.y + setback + usable_length * y_bias + rng.uniform(-1.0, 1.0)
    return Rect(round(max(site.x + setback, x), 2), round(max(site.y + setback, y), 2), width, length)


def _rooms_for_floor(requirements: list[RoomRequirement], floor: int, footprint: Rect, floors: int, variant: int) -> list[Room]:
    reqs = [room for room in requirements if room.type != "parking"]
    if floor == 1:
        rooms = _ground_floor_rooms(reqs, footprint.width, footprint.height, variant)
    else:
        rooms = _upper_floor_rooms(reqs, footprint.width, footprint.height, floor, variant)
    return rooms


def _ground_floor_rooms(requirements: list[RoomRequirement], width: float, length: float, variant: int) -> list[Room]:
    room_by_id = {room.id: room for room in requirements}
    rooms: list[Room] = []
    front_h = max(17.0, length * 0.34)
    mid_h = max(10.0, length * 0.25)
    rear_h = max(9.0, length - front_h - mid_h)
    left_w = width * (0.58 if variant % 2 == 0 else 0.52)
    right_w = width - left_w
    hall_w = min(5.5, max(4.0, width * 0.12))

    _add(rooms, room_by_id, "entrance", width * 0.38, 0, width * 0.24, 6.0)
    room_left_w = max(10.0, left_w - hall_w)
    _add(rooms, room_by_id, "living", 0, 6.0, room_left_w, front_h - 6.0)
    _add(rooms, room_by_id, "dining", 0, front_h, room_left_w, mid_h)
    _add(rooms, room_by_id, "kitchen", left_w, front_h, right_w, mid_h)
    _add(rooms, room_by_id, "stairs", left_w, 6.0, min(9.0, right_w), 10.5)
    _add(rooms, room_by_id, "bathroom_2", left_w + min(9.0, right_w), 6.0, max(7.0, right_w - min(9.0, right_w)), 8.0)
    if "stairs" not in room_by_id and "bathroom_2" not in room_by_id and right_w >= 10.0:
        rooms.append(Room("flex_front", "utility", "Store / Flex", 1, left_w, 6.0, right_w, max(8.0, front_h - 6.0), round(right_w * max(8.0, front_h - 6.0), 2), "service"))
    _add(rooms, room_by_id, "office", 0, front_h + mid_h, min(room_left_w, 13.0), 10.0)
    _add(rooms, room_by_id, "utility", left_w + right_w * 0.5, front_h + mid_h, right_w * 0.5, min(8.0, rear_h))

    rear_y = front_h + mid_h
    if "master_bedroom" in room_by_id:
        master_w = max(11.0, room_left_w * 0.52)
        private_h = max(9.5, min(12.5, length - rear_y))
        _add(rooms, room_by_id, "master_bedroom", 0, rear_y, master_w, private_h)
        for bedroom_index, req in enumerate([req for req in requirements if req.type == "bedroom"]):
            _add_req(rooms, req, master_w + bedroom_index * max(9.0, room_left_w - master_w), rear_y, max(9.0, room_left_w - master_w), private_h, 1)
        _add(rooms, room_by_id, "bathroom_1", left_w, rear_y, min(8.5, right_w), 8.0)
        bath_w = min(8.5, right_w)
        if "utility" not in room_by_id and right_w - bath_w >= 6.0 and length - rear_y >= 8.0:
            rooms.append(Room("utility_flex", "utility", "Utility / Store", 1, left_w + bath_w, rear_y, right_w - bath_w, length - rear_y, round((right_w - bath_w) * (length - rear_y), 2), "service"))

    if not any(room.type == "bathroom" for room in rooms):
        _add_first_type(rooms, requirements, "bathroom", left_w, 6.0, min(8.0, right_w), 8.0)

    corridor_y = front_h + mid_h
    rooms.append(Room("hall_ground", "hallway", "Hall", 1, left_w - hall_w, 6.0, hall_w, max(8.0, corridor_y - 6.0), round(hall_w * max(8.0, corridor_y - 6.0), 2), "circulation"))

    _pack_unplaced(rooms, requirements, width, length, 0, corridor_y, room_left_w - 1.0, max(8.0, length - corridor_y), 1)
    return _trim_rooms(rooms, width, length)


def _upper_floor_rooms(requirements: list[RoomRequirement], width: float, length: float, floor: int, variant: int) -> list[Room]:
    room_by_id = {room.id: room for room in requirements}
    rooms: list[Room] = []
    landing_w = min(9.0, width * 0.2)
    landing_h = 10.5
    center_x = width * 0.62
    center_y = 6.0

    if "stairs" not in room_by_id:
        rooms.append(Room(f"stairs_floor_{floor}", "staircase", "Staircase", floor, center_x, center_y, landing_w, landing_h, round(landing_w * landing_h, 2), "circulation"))
    landing_length = min(16.0, max(10.0, length - center_y - landing_h - 8.0))
    rooms.append(Room(f"landing_{floor}", "hallway", "Landing", floor, center_x, center_y + landing_h, landing_w, landing_length, round(landing_w * landing_length, 2), "circulation"))

    _add(rooms, room_by_id, "master_bedroom", 0, 0, width * 0.42, max(13.0, length * 0.35), floor)
    _add(rooms, room_by_id, "bathroom_1", width * 0.42, 0, min(8.5, width * 0.2), 8.5, floor)
    _add(rooms, room_by_id, "family_lounge", 0, max(17.5, length * 0.38), center_x - 1.0, 9.0, floor)
    _add(rooms, room_by_id, "balcony", 0, length - 6.0, width * 0.42, 6.0, floor)

    bedroom_reqs = [req for req in requirements if req.type == "bedroom"]
    positions = [
        (0, max(25.0, length * 0.56), center_x - 1.0, 12.0),
        (center_x + landing_w + 1.0, 17.0, max(8.0, width - (center_x + landing_w + 1.0)), 12.0),
        (center_x + landing_w + 1.0, 30.0, max(8.0, width - (center_x + landing_w + 1.0)), 10.5),
        (center_x + landing_w + 1.0, 30.0, max(8.0, width - (center_x + landing_w + 1.0)), 10.5),
    ]
    for index, req in enumerate(bedroom_reqs):
        x, y, room_w, room_h = positions[index % len(positions)]
        _add_req(rooms, req, x, y, room_w, room_h, floor)

    shared_baths = [req for req in requirements if req.type == "bathroom" and req.id != "bathroom_1"]
    bx = center_x + landing_w + 1.0
    by = max(42.0, length * 0.85)
    for index, req in enumerate(shared_baths):
        if any(room.id == req.id for room in rooms):
            continue
        _add_req(rooms, req, bx, by + index * 8.5, min(8.5, width - bx), 8.0, floor)

    _pack_unplaced(rooms, requirements, width, length, 0, by + len(shared_baths) * 8.5, center_x - 1.0, max(8.0, length - by), floor)
    return _trim_rooms(rooms, width, length)


def _add(rooms: list[Room], room_by_id: dict[str, RoomRequirement], room_id: str, x: float, y: float, width: float, height: float, floor: int = 1) -> None:
    req = room_by_id.get(room_id)
    if req:
        _add_req(rooms, req, x, y, width, height, floor)


def _add_first_type(rooms: list[Room], requirements: list[RoomRequirement], room_type: str, x: float, y: float, width: float, height: float) -> None:
    for req in requirements:
        if req.type == room_type and not any(room.id == req.id for room in rooms):
            _add_req(rooms, req, x, y, width, height, 1)
            return


def _add_req(rooms: list[Room], req: RoomRequirement, x: float, y: float, width: float, height: float, floor: int) -> None:
    width = max(6.0, round(width, 2))
    height = max(5.0, round(height, 2))
    rooms.append(Room(req.id, req.type, req.label, floor, round(x, 2), round(y, 2), width, height, round(width * height, 2), ZONE_BY_TYPE.get(req.type, "private")))


def _pack_unplaced(rooms: list[Room], requirements: list[RoomRequirement], width: float, length: float, x: float, y: float, pack_w: float, pack_h: float, floor: int) -> None:
    cursor_x = x
    cursor_y = y
    row_h = 0.0
    for req in sorted(requirements, key=lambda item: (-item.priority, item.id)):
        if any(room.id == req.id for room in rooms):
            continue
        room_w = min(max(8.0, math.sqrt(req.preferred_area * 1.1)), max(7.0, pack_w))
        room_h = min(max(7.0, req.preferred_area / room_w), max(6.0, pack_h))
        if cursor_x + room_w > x + pack_w:
            cursor_x = x
            cursor_y += row_h + 1.0
            row_h = 0.0
        if cursor_y + room_h > length:
            cursor_y = max(0, length - room_h)
        _add_req(rooms, req, cursor_x, cursor_y, room_w, room_h, floor)
        cursor_x += room_w + 1.0
        row_h = max(row_h, room_h)


def _trim_rooms(rooms: list[Room], width: float, length: float) -> list[Room]:
    trimmed = []
    for room in rooms:
        room.width = round(max(0.1, min(room.width, width - room.x)), 2)
        room.height = round(max(0.1, min(room.height, length - room.y)), 2)
        room.area_sqft = round(room.width * room.height, 2)
        trimmed.append(room)
    return trimmed


def _parking_for_request(request: PlanningRequest, footprint: Rect) -> Parking | None:
    if not request.parking_spaces:
        return None
    spaces = request.parking_spaces
    return Parking(spaces=spaces, x=footprint.x, y=footprint.top + 3.0, width=10.0 * spaces, height=16.0)


def _enrich_architectural_geometry(plan: CandidatePlan) -> None:
    plan.zones = {}
    for room in plan.rooms:
        plan.zones.setdefault(room.zone, []).append(room.id)
    plan.walls = _build_walls(plan)
    plan.access_graph = _build_access_graph(plan)
    plan.circulation = {key: value for key, value in plan.access_graph.items() if key.startswith("hall") or key.startswith("landing") or key.startswith("entrance") or key.startswith("stairs")}
    plan.doors = _build_doors(plan)
    plan.windows = _build_windows(plan)
    plan.fixtures = _build_fixtures(plan)
    plan.dimensions = _build_dimensions(plan)
    usable = round(sum(room.area_sqft for room in plan.rooms if room.zone != "circulation"), 2)
    circulation = round(sum(room.area_sqft for room in plan.rooms if room.zone == "circulation"), 2)
    footprint_area = round(plan.footprint.area * plan.floors, 2)
    unused = round(max(0.0, footprint_area - usable - circulation), 2)
    plan.space_metrics = {
        "usable_room_area": usable,
        "circulation_area": circulation,
        "unused_area": unused,
        "footprint_area": footprint_area,
        "space_efficiency_score": round(max(0.0, min(100.0, (usable + circulation * 0.65) / max(1.0, footprint_area) * 100)), 2),
    }


def _build_walls(plan: CandidatePlan) -> list[Wall]:
    walls: list[Wall] = []
    for floor in range(1, plan.floors + 1):
        w = plan.footprint.width
        h = plan.footprint.height
        walls.extend(
            [
                Wall(f"floor_{floor}_front", floor, "exterior", 0, 0, w, 0, EXTERIOR_WALL_THICKNESS, ["external"]),
                Wall(f"floor_{floor}_right", floor, "exterior", w, 0, w, h, EXTERIOR_WALL_THICKNESS, ["external"]),
                Wall(f"floor_{floor}_rear", floor, "exterior", w, h, 0, h, EXTERIOR_WALL_THICKNESS, ["external"]),
                Wall(f"floor_{floor}_left", floor, "exterior", 0, h, 0, 0, EXTERIOR_WALL_THICKNESS, ["external"]),
            ]
        )
        for room in [room for room in plan.rooms if room.floor_number == floor]:
            walls.append(Wall(f"{room.id}_partition", floor, "interior", room.x, room.y, room.x + room.width, room.y, INTERIOR_WALL_THICKNESS, [room.id]))
    return walls


def _build_access_graph(plan: CandidatePlan) -> dict[str, list[str]]:
    graph: dict[str, list[str]] = {}
    by_floor = {floor: [room for room in plan.rooms if room.floor_number == floor] for floor in range(1, plan.floors + 1)}
    for floor, rooms in by_floor.items():
        circulation = [room for room in rooms if room.zone == "circulation" or room.type in {"entrance", "living_room", "dining", "family_lounge"}]
        hubs = [room for room in circulation if room.type in {"hallway", "entrance", "staircase"}]
        if not hubs and circulation:
            hubs = [circulation[0]]
        for room in rooms:
            graph.setdefault(room.id, [])
            if room in hubs:
                continue
            hub = _nearest(room, hubs or circulation)
            if hub:
                _connect(graph, room.id, hub.id)
        for index, hub in enumerate(hubs[:-1]):
            _connect(graph, hub.id, hubs[index + 1].id)
    if plan.floors > 1:
        stairs = [room for room in plan.rooms if room.type == "staircase"]
        for stair in stairs[1:]:
            _connect(graph, stairs[0].id, stair.id)
    if plan.parking:
        graph.setdefault("parking", [])
        _connect(graph, "parking", "entrance")
    _connect(graph, "entrance", "living")
    _connect(graph, "living", "dining")
    _connect(graph, "dining", "kitchen")
    _connect(graph, "master_bedroom", "bathroom_1")
    return graph


def _connect(graph: dict[str, list[str]], a: str, b: str) -> None:
    if not a or not b or a == b:
        return
    graph.setdefault(a, [])
    graph.setdefault(b, [])
    if b not in graph[a]:
        graph[a].append(b)
    if a not in graph[b]:
        graph[b].append(a)


def _nearest(room: Room, others: list[Room]) -> Room | None:
    if not others:
        return None
    return min(others, key=lambda other: (room.x + room.width / 2 - other.x - other.width / 2) ** 2 + (room.y + room.height / 2 - other.y - other.height / 2) ** 2)


def _build_doors(plan: CandidatePlan) -> list[Door]:
    doors = [Door("main_entry", 1, ["external", "entrance"], "floor_1_front", 0.5, 3.5, "inward", "main", plan.footprint.width * 0.5, 0, "horizontal")]
    for room in plan.rooms:
        if room.id == "entrance":
            continue
        connected = plan.access_graph.get(room.id, [])
        if not connected:
            continue
        target = connected[0]
        x = room.x + room.width / 2
        y = room.y
        orientation = "horizontal"
        doors.append(Door(f"door_{room.id}", room.floor_number, [target, room.id], f"{room.id}_partition", 0.5, 2.8 if room.type == "bathroom" else 3.0, "inward", "internal", round(x, 2), round(y, 2), orientation))
    return doors


def _build_windows(plan: CandidatePlan) -> list[Window]:
    windows: list[Window] = []
    window_types = {"bedroom", "master_bedroom", "living_room", "dining", "kitchen", "office", "family_lounge"}
    for room in plan.rooms:
        if room.type not in window_types:
            continue
        if room.y <= 0.1:
            wall, x, y, orientation = f"floor_{room.floor_number}_front", room.x + room.width / 2, 0.0, "horizontal"
        elif room.x <= 0.1:
            wall, x, y, orientation = f"floor_{room.floor_number}_left", 0.0, room.y + room.height / 2, "vertical"
        elif room.x + room.width >= plan.footprint.width - 0.1:
            wall, x, y, orientation = f"floor_{room.floor_number}_right", plan.footprint.width, room.y + room.height / 2, "vertical"
        elif room.y + room.height >= plan.footprint.height - 0.1:
            wall, x, y, orientation = f"floor_{room.floor_number}_rear", room.x + room.width / 2, plan.footprint.height, "horizontal"
        else:
            continue
        windows.append(Window(f"window_{room.id}", room.floor_number, room.id, wall, 0.5, min(5.0, max(3.0, room.width * 0.35)), round(x, 2), round(y, 2), orientation))
    return windows


def _build_fixtures(plan: CandidatePlan) -> list[Fixture]:
    fixtures: list[Fixture] = []
    for room in plan.rooms:
        x, y = room.x + 1.0, room.y + 1.0
        if room.type in {"bedroom", "master_bedroom"}:
            fixtures.append(Fixture(f"bed_{room.id}", room.floor_number, room.id, "bed", x, y, min(6.0, room.width - 2), min(6.5, room.height - 2), "BED"))
            fixtures.append(Fixture(f"robe_{room.id}", room.floor_number, room.id, "wardrobe", room.x + room.width - 2.2, room.y + 1, 1.4, min(6, room.height - 2)))
        elif room.type == "living_room":
            fixtures.extend([Fixture(f"sofa_{room.id}", room.floor_number, room.id, "sofa", x, y, 6, 2.5), Fixture(f"tv_{room.id}", room.floor_number, room.id, "tv", room.x + room.width - 1.2, room.y + 2, 0.8, 5)])
        elif room.type == "dining":
            fixtures.append(Fixture(f"table_{room.id}", room.floor_number, room.id, "dining_table", room.x + room.width / 2 - 2.5, room.y + room.height / 2 - 1.5, 5, 3))
        elif room.type == "kitchen":
            fixtures.extend([Fixture(f"counter_{room.id}", room.floor_number, room.id, "counter", x, y, room.width - 2, 2), Fixture(f"sink_{room.id}", room.floor_number, room.id, "sink", x + 2, y + 0.3, 2, 1.2), Fixture(f"cooker_{room.id}", room.floor_number, room.id, "cooker", x + 5, y + 0.3, 2, 1.2)])
        elif room.type == "bathroom":
            fixtures.extend([Fixture(f"wc_{room.id}", room.floor_number, room.id, "wc", x, y, 2, 2), Fixture(f"basin_{room.id}", room.floor_number, room.id, "basin", x + 2.5, y, 2, 1.4), Fixture(f"shower_{room.id}", room.floor_number, room.id, "shower", room.x + room.width - 3, room.y + room.height - 3, 2.5, 2.5)])
        elif room.type == "office":
            fixtures.append(Fixture(f"desk_{room.id}", room.floor_number, room.id, "desk", x, y, 5, 2.5))
        elif room.type == "staircase":
            fixtures.append(Fixture(f"stair_{room.id}", room.floor_number, room.id, "stair_treads", room.x, room.y, room.width, room.height, "UP" if room.floor_number == 1 else "DN"))
    if plan.parking:
        for index in range(plan.parking.spaces):
            fixtures.append(Fixture(f"car_{index + 1}", 1, "parking", "vehicle", plan.parking.x - plan.footprint.x + index * 10.0 + 0.8, plan.parking.y - plan.footprint.y + 1.0, 8.4, 13.5, f"CAR {index + 1}"))
    return fixtures


def _build_dimensions(plan: CandidatePlan) -> list[Dimension]:
    dimensions: list[Dimension] = []
    for floor in range(1, plan.floors + 1):
        dimensions.append(Dimension(f"overall_width_{floor}", floor, _feet_label(plan.footprint.width), 0, 0, plan.footprint.width, 0, -4.0, "overall"))
        dimensions.append(Dimension(f"overall_length_{floor}", floor, _feet_label(plan.footprint.height), plan.footprint.width, 0, plan.footprint.width, plan.footprint.height, 4.0, "overall"))
        for room in [room for room in plan.rooms if room.floor_number == floor]:
            dimensions.append(Dimension(f"dim_{room.id}", floor, f"{_feet_label(room.width)} x {_feet_label(room.height)}", room.x, room.y, room.x + room.width, room.y, 1.0, "room"))
    return dimensions


def _feet_label(value: float) -> str:
    feet = int(value)
    inches = round((value - feet) * 12)
    if inches == 12:
        feet += 1
        inches = 0
    return f"{feet}'-{inches}\""
