from app.agents.agent3_planning.adjacency import adjacency_score
from app.agents.agent3_planning.models import CandidatePlan, RoomRequirement


WEIGHTS = {
    "requirement_satisfaction": 0.25,
    "adjacency_quality": 0.20,
    "circulation_quality": 0.15,
    "space_efficiency": 0.15,
    "privacy": 0.10,
    "natural_light_potential": 0.05,
    "compactness": 0.05,
    "parking_entrance_relationship": 0.05,
}


def score_candidate(candidate: CandidatePlan, program: list[RoomRequirement]) -> CandidatePlan:
    required = [room for room in program if room.required and room.type != "parking"]
    present = {room.id for room in candidate.rooms}
    requirement_satisfaction = len([room for room in required if room.id in present]) / max(1, len(required)) * 100

    space_efficiency = candidate.space_metrics.get("space_efficiency_score", 0.0)
    circulation_quality = _circulation_quality(candidate)
    privacy = _privacy_score(candidate)
    natural_light = _natural_light_score(candidate)
    compactness = _compactness_score(candidate)
    parking_entry = _parking_entrance_score(candidate)
    breakdown = {
        "requirement_satisfaction": round(requirement_satisfaction, 2),
        "adjacency_quality": adjacency_score(candidate),
        "space_efficiency": round(space_efficiency, 2),
        "circulation_quality": round(circulation_quality, 2),
        "privacy": round(privacy, 2),
        "natural_light_potential": round(natural_light, 2),
        "compactness": round(compactness, 2),
        "parking_entrance_relationship": round(parking_entry, 2),
    }
    total = sum(breakdown[key] * weight for key, weight in WEIGHTS.items())
    candidate.score = round(total, 2)
    candidate.score_breakdown = breakdown
    return candidate


def _circulation_quality(candidate: CandidatePlan) -> float:
    required = {room.id for room in candidate.rooms if room.zone != "external"}
    reachable = _reachable(candidate, "entrance")
    connectivity = len(required & reachable) / max(1, len(required)) * 100
    circulation_area = candidate.space_metrics.get("circulation_area", 0.0)
    footprint_area = candidate.space_metrics.get("footprint_area", 1.0)
    circulation_ratio = circulation_area / max(1.0, footprint_area)
    penalty = 0.0
    if circulation_ratio > 0.18:
        penalty = min(25.0, (circulation_ratio - 0.18) * 180)
    return max(0.0, connectivity - penalty)


def _privacy_score(candidate: CandidatePlan) -> float:
    public = {room.id for room in candidate.rooms if room.zone == "public"}
    private = [room.id for room in candidate.rooms if room.zone == "private"]
    if not private:
        return 100.0
    direct_public_private = sum(1 for room_id in private if public & set(candidate.access_graph.get(room_id, [])))
    return max(45.0, 95.0 - direct_public_private * 12.0)


def _natural_light_score(candidate: CandidatePlan) -> float:
    needs_light = [room.id for room in candidate.rooms if room.type in {"bedroom", "master_bedroom", "living_room", "dining", "kitchen", "office", "family_lounge"}]
    with_window = {window.room_id for window in candidate.windows}
    return len(set(needs_light) & with_window) / max(1, len(needs_light)) * 100


def _compactness_score(candidate: CandidatePlan) -> float:
    unused = candidate.space_metrics.get("unused_area", 0.0)
    footprint = candidate.space_metrics.get("footprint_area", 1.0)
    unused_ratio = unused / max(1.0, footprint)
    return max(0.0, 100.0 - unused_ratio * 180.0)


def _parking_entrance_score(candidate: CandidatePlan) -> float:
    if not candidate.parking:
        return 100.0
    return 100.0 if "entrance" in candidate.access_graph.get("parking", []) else 25.0


def _reachable(candidate: CandidatePlan, start: str) -> set[str]:
    visited = set()
    stack = [start]
    while stack:
        node = stack.pop()
        if node in visited:
            continue
        visited.add(node)
        stack.extend(candidate.access_graph.get(node, []))
    return visited
