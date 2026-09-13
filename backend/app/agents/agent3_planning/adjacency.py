import json
from pathlib import Path

from app.agents.agent3_planning.geometry import room_rect
from app.agents.agent3_planning.models import CandidatePlan

ROOT = Path(__file__).resolve().parents[4]
ADJACENCY_PATH = ROOT / "data" / "knowledge" / "adjacency_rules.json"


def load_adjacency_rules() -> list[dict]:
    with ADJACENCY_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)["rules"]


def adjacency_score(candidate: CandidatePlan) -> float:
    rooms_by_type = {}
    for room in candidate.rooms:
        rooms_by_type.setdefault(room.type, []).append(room)

    rules = load_adjacency_rules()
    if not rules:
        return 100.0

    satisfied = 0
    checked = 0
    for rule in rules:
        left_rooms = rooms_by_type.get(rule["from"], [])
        right_rooms = rooms_by_type.get(rule["to"], [])
        if not left_rooms or not right_rooms:
            continue
        checked += 1
        best = max(_pair_adjacency(a, b, float(rule.get("preferred_max_distance_ft", 18))) for a in left_rooms for b in right_rooms)
        satisfied += best
    if checked == 0:
        return 100.0
    return round(satisfied / checked * 100, 2)


def _pair_adjacency(a, b, preferred_distance: float) -> float:
    if a.floor_number != b.floor_number:
        return 0.25
    if _shared_wall_length(room_rect(a), room_rect(b)) >= 3.0:
        return 1.0
    gap = _rect_gap(room_rect(a), room_rect(b))
    if gap <= 2.0:
        return 0.85
    if gap <= preferred_distance:
        return 0.6
    return 0.0


def _shared_wall_length(a, b) -> float:
    vertical_touch = abs(a.right - b.x) < 0.1 or abs(b.right - a.x) < 0.1
    horizontal_touch = abs(a.top - b.y) < 0.1 or abs(b.top - a.y) < 0.1
    if vertical_touch:
        return max(0.0, min(a.top, b.top) - max(a.y, b.y))
    if horizontal_touch:
        return max(0.0, min(a.right, b.right) - max(a.x, b.x))
    return 0.0


def _rect_gap(a, b) -> float:
    dx = max(b.x - a.right, a.x - b.right, 0)
    dy = max(b.y - a.top, a.y - b.top, 0)
    return (dx * dx + dy * dy) ** 0.5
