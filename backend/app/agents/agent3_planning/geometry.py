from app.agents.agent3_planning.models import Rect, Room


def rectangles_overlap(a: Rect, b: Rect) -> bool:
    epsilon = 0.05
    return not (a.right <= b.x + epsilon or b.right <= a.x + epsilon or a.top <= b.y + epsilon or b.top <= a.y + epsilon)


def room_rect(room: Room) -> Rect:
    return Rect(room.x, room.y, room.width, room.height)


def inside(inner: Rect, outer: Rect) -> bool:
    epsilon = 0.05
    return inner.x >= outer.x - epsilon and inner.y >= outer.y - epsilon and inner.right <= outer.right + epsilon and inner.top <= outer.top + epsilon
