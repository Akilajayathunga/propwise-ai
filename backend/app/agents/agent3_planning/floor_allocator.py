from collections import defaultdict

from app.agents.agent3_planning.models import RoomRequirement


def allocate_floors(program: list[RoomRequirement], floors: int) -> dict[int, list[RoomRequirement]]:
    allocation: dict[int, list[RoomRequirement]] = defaultdict(list)
    for room in program:
        floor = room.floor_preference or 1
        floor = min(max(1, floor), floors)
        allocation[floor].append(room)
    for floor in range(1, floors + 1):
        allocation.setdefault(floor, [])
    return dict(allocation)

