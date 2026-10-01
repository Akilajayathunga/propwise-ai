from app.agents.agent3_planning.constraints import validate_candidate
from app.agents.agent3_planning.models import CandidatePlan, RoomRequirement
from app.agents.agent3_planning.scoring import score_candidate


def select_best_candidate(
    candidates: list[CandidatePlan],
    program: list[RoomRequirement],
) -> tuple[CandidatePlan | None, list[CandidatePlan], list[str]]:
    valid: list[CandidatePlan] = []
    rejection_reasons: list[str] = []
    for candidate in candidates:
        is_valid, errors = validate_candidate(candidate, program)
        if is_valid:
            valid.append(score_candidate(candidate, program))
        else:
            rejection_reasons.extend(errors)

    if not valid:
        return None, [], sorted(set(rejection_reasons))

    valid.sort(key=lambda item: item.score or 0.0, reverse=True)
    return valid[0], valid, sorted(set(rejection_reasons))

