from app.agents.agent3_planning.adjacency import adjacency_score
from app.agents.agent3_planning.models import CandidatePlan, RoomRequirement


WEIGHTS = {
    "requirement_satisfaction": 0.30,
    "adjacency_quality": 0.20,
    "space_efficiency": 0.18,
    "circulation_efficiency": 0.12,
    "privacy": 0.10,
    "compactness": 0.10,
}


def score_candidate(candidate: CandidatePlan, program: list[RoomRequirement]) -> CandidatePlan:
    required = [room for room in program if room.required and room.type != "parking"]
    present = {room.id for room in candidate.rooms}
    requirement_satisfaction = len([room for room in required if room.id in present]) / max(1, len(required)) * 100

    preferred_area = sum(room.preferred_area for room in program if room.type != "parking")
    actual_area = sum(room.area_sqft for room in candidate.rooms)
    space_efficiency = min(100.0, preferred_area / actual_area * 100) if actual_area else 0.0
    circulation_efficiency = max(60.0, min(100.0, 100.0 - len(candidate.rooms) * 1.3))
    privacy = 92.0 if candidate.floors > 1 else 76.0
    compactness = min(100.0, candidate.footprint.area / max(actual_area, 1.0) * 65.0)
    breakdown = {
        "requirement_satisfaction": round(requirement_satisfaction, 2),
        "adjacency_quality": adjacency_score(candidate),
        "space_efficiency": round(space_efficiency, 2),
        "circulation_efficiency": round(circulation_efficiency, 2),
        "privacy": privacy,
        "compactness": round(compactness, 2),
    }
    total = sum(breakdown[key] * weight for key, weight in WEIGHTS.items())
    candidate.score = round(total, 2)
    candidate.score_breakdown = breakdown
    return candidate

