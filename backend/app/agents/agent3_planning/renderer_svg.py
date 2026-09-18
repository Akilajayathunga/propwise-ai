from pathlib import Path

from app.agents.agent3_planning.models import CandidatePlan, Dimension, Door, Fixture, Room, Window


SCALE = 10
MARGIN = 112


def render_svg(plan: CandidatePlan, output_dir: Path) -> list[str]:
    paths: list[str] = []
    output_dir.mkdir(parents=True, exist_ok=True)
    for floor in range(1, plan.floors + 1):
        floor_name = "ground_floor" if floor == 1 else f"floor_{floor}"
        path = output_dir / f"{floor_name}.svg"
        path.write_text(_svg_for_floor(plan, floor), encoding="utf-8")
        paths.append(str(path))
    return paths


def _svg_for_floor(plan: CandidatePlan, floor: int) -> str:
    drawing_width = int(plan.footprint.width * SCALE + MARGIN * 2 + 120)
    parking_extra = int((plan.parking.height + 9) * SCALE) if floor == 1 and plan.parking else 0
    drawing_height = int(plan.footprint.height * SCALE + MARGIN * 2 + 90 + parking_extra)
    title = "GROUND FLOOR" if floor == 1 else f"FLOOR {floor}"
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{drawing_width}" height="{drawing_height}" viewBox="0 0 {drawing_width} {drawing_height}" preserveAspectRatio="xMidYMid meet">',
        "<defs>",
        '<marker id="tick" markerWidth="8" markerHeight="8" refX="4" refY="4" orient="auto"><path d="M1,7 L7,1" stroke="#27322e" stroke-width="1.4"/></marker>',
        "</defs>",
        '<rect width="100%" height="100%" fill="#f6f5f1"/>',
        f'<text x="{MARGIN}" y="34" font-family="Arial" font-size="18" font-weight="700" fill="#1d2522">{title} - CONCEPTUAL RESIDENTIAL PLAN</text>',
        f'<text x="{MARGIN}" y="52" font-family="Arial" font-size="11" fill="#6a746f">Conceptual AI-assisted plan - not construction-ready</text>',
        _north_arrow(drawing_width - 72, 42),
        _site_context(plan, floor),
        _exterior_walls(plan),
    ]

    rooms = [room for room in plan.rooms if room.floor_number == floor]
    parts.extend(_room_fill(room) for room in rooms if room.zone != "external")
    parts.extend(_partition(room) for room in rooms)
    parts.extend(_window_symbol(window) for window in plan.windows if window.floor_number == floor)
    parts.extend(_door_symbol(door) for door in plan.doors if door.floor_number == floor)
    parts.extend(_fixture_symbol(fixture) for fixture in plan.fixtures if fixture.floor_number == floor)
    parts.extend(_room_label(room) for room in rooms)
    parts.extend(_dimension_line(dimension) for dimension in plan.dimensions if dimension.floor_number == floor and dimension.dimension_type == "overall")

    if floor == 1 and plan.parking:
        parts.append(_parking(plan))

    parts.append(f'<text x="{MARGIN}" y="{drawing_height - 24}" font-family="Arial" font-size="10" fill="#6a746f">Scale is conceptual. Verify all dimensions and approvals with qualified professionals.</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def _tx(x: float) -> float:
    return MARGIN + x * SCALE


def _ty(y: float) -> float:
    return MARGIN + y * SCALE


def _room_fill(room: Room) -> str:
    fills = {
        "public": "#f7fbf8",
        "service": "#f8f7f0",
        "private": "#fbfaf7",
        "circulation": "#f0f3f1",
    }
    return f'<rect x="{_tx(room.x):.1f}" y="{_ty(room.y):.1f}" width="{room.width * SCALE:.1f}" height="{room.height * SCALE:.1f}" fill="{fills.get(room.zone, "#ffffff")}"/>'


def _partition(room: Room) -> str:
    stroke = "#3f4a45" if room.zone != "external" else "#62706a"
    dash = ' stroke-dasharray="5 4"' if room.zone == "external" else ""
    return f'<rect x="{_tx(room.x):.1f}" y="{_ty(room.y):.1f}" width="{room.width * SCALE:.1f}" height="{room.height * SCALE:.1f}" fill="none" stroke="{stroke}" stroke-width="1.8"{dash}/>'


def _exterior_walls(plan: CandidatePlan) -> str:
    return f'<rect x="{MARGIN}" y="{MARGIN}" width="{plan.footprint.width * SCALE:.1f}" height="{plan.footprint.height * SCALE:.1f}" fill="none" stroke="#111815" stroke-width="7" stroke-linejoin="miter"/>'


def _door_symbol(door: Door) -> str:
    x = _tx(door.x)
    y = _ty(door.y)
    w = door.width * SCALE
    color = "#ffffff" if door.door_type == "main" else "#f6f5f1"
    if door.orientation == "vertical":
        opening = f'<line x1="{x:.1f}" y1="{y - w / 2:.1f}" x2="{x:.1f}" y2="{y + w / 2:.1f}" stroke="{color}" stroke-width="8"/>'
        leaf = f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x + w:.1f}" y2="{y:.1f}" stroke="#222b27" stroke-width="1.5"/>'
        arc = f'<path d="M{x:.1f},{y - w:.1f} A{w:.1f},{w:.1f} 0 0 1 {x + w:.1f},{y:.1f}" fill="none" stroke="#68736e" stroke-width="1"/>'
    else:
        opening = f'<line x1="{x - w / 2:.1f}" y1="{y:.1f}" x2="{x + w / 2:.1f}" y2="{y:.1f}" stroke="{color}" stroke-width="8"/>'
        leaf = f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x:.1f}" y2="{y + w:.1f}" stroke="#222b27" stroke-width="1.5"/>'
        arc = f'<path d="M{x + w:.1f},{y:.1f} A{w:.1f},{w:.1f} 0 0 1 {x:.1f},{y + w:.1f}" fill="none" stroke="#68736e" stroke-width="1"/>'
    return f'<g class="door" data-door="{_esc(door.id)}">{opening}{leaf}{arc}</g>'


def _window_symbol(window: Window) -> str:
    x = _tx(window.x)
    y = _ty(window.y)
    w = window.width * SCALE
    if window.orientation == "vertical":
        return f'<g class="window"><line x1="{x:.1f}" y1="{y - w / 2:.1f}" x2="{x:.1f}" y2="{y + w / 2:.1f}" stroke="#f6f5f1" stroke-width="8"/><line x1="{x - 3:.1f}" y1="{y - w / 2:.1f}" x2="{x - 3:.1f}" y2="{y + w / 2:.1f}" stroke="#198da0" stroke-width="1.4"/><line x1="{x + 3:.1f}" y1="{y - w / 2:.1f}" x2="{x + 3:.1f}" y2="{y + w / 2:.1f}" stroke="#198da0" stroke-width="1.4"/></g>'
    return f'<g class="window"><line x1="{x - w / 2:.1f}" y1="{y:.1f}" x2="{x + w / 2:.1f}" y2="{y:.1f}" stroke="#f6f5f1" stroke-width="8"/><line x1="{x - w / 2:.1f}" y1="{y - 3:.1f}" x2="{x + w / 2:.1f}" y2="{y - 3:.1f}" stroke="#198da0" stroke-width="1.4"/><line x1="{x - w / 2:.1f}" y1="{y + 3:.1f}" x2="{x + w / 2:.1f}" y2="{y + 3:.1f}" stroke="#198da0" stroke-width="1.4"/></g>'


def _fixture_symbol(fixture: Fixture) -> str:
    x = _tx(fixture.x)
    y = _ty(fixture.y)
    w = fixture.width * SCALE
    h = fixture.height * SCALE
    label = _esc(fixture.label or "")
    if fixture.fixture_type == "stair_treads":
        steps = []
        for index in range(1, 7):
            yy = y + h * index / 7
            steps.append(f'<line x1="{x:.1f}" y1="{yy:.1f}" x2="{x + w:.1f}" y2="{yy:.1f}" stroke="#56615c" stroke-width="1"/>')
        steps.append(f'<text x="{x + w / 2:.1f}" y="{y + h / 2:.1f}" text-anchor="middle" font-family="Arial" font-size="10" font-weight="700" fill="#1d2522">{label}</text>')
        return f'<g class="stairs">{"".join(steps)}<path d="M{x + w / 2:.1f},{y + h - 8:.1f} L{x + w / 2:.1f},{y + 8:.1f} M{x + w / 2 - 4:.1f},{y + 12:.1f} L{x + w / 2:.1f},{y + 8:.1f} L{x + w / 2 + 4:.1f},{y + 12:.1f}" stroke="#1d2522" fill="none"/></g>'
    if fixture.fixture_type == "vehicle":
        return f'<g class="vehicle"><rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="10" fill="none" stroke="#56615c" stroke-width="1.5"/><text x="{x + w / 2:.1f}" y="{y + h / 2:.1f}" text-anchor="middle" font-family="Arial" font-size="9" fill="#43524d">{label}</text></g>'
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="2" fill="none" stroke="#7a8580" stroke-width="1"/>'


def _room_label(room: Room) -> str:
    x = _tx(room.x + room.width / 2)
    y = _ty(room.y + room.height / 2)
    name = _esc(_fit_label(_short_label(room.label), room.width))
    dims = f"{_feet_label(room.width)} x {_feet_label(room.height)}"
    box_w = min(room.width * SCALE - 8, max(62, len(name) * 6.5))
    return (
        f'<g class="room-label"><rect x="{x - box_w / 2:.1f}" y="{y - 22:.1f}" width="{box_w:.1f}" height="40" rx="4" fill="#ffffff" stroke="#d8ded8" stroke-width="0.8"/>'
        f'<text x="{x:.1f}" y="{y - 7:.1f}" text-anchor="middle" font-family="Arial" font-size="10" font-weight="700" fill="#1d2522">{name}</text>'
        f'<text x="{x:.1f}" y="{y + 6:.1f}" text-anchor="middle" font-family="Arial" font-size="8.5" fill="#4f5b55">{dims}</text>'
        f'<text x="{x:.1f}" y="{y + 18:.1f}" text-anchor="middle" font-family="Arial" font-size="8" fill="#6a746f">{room.area_sqft:.0f} sq.ft</text></g>'
    )


def _dimension_line(dimension: Dimension) -> str:
    x1 = _tx(dimension.x1)
    y1 = _ty(dimension.y1)
    x2 = _tx(dimension.x2)
    y2 = _ty(dimension.y2)
    if abs(y1 - y2) < 0.1:
        y1 += dimension.offset * SCALE
        y2 += dimension.offset * SCALE
        text_x, text_y = (x1 + x2) / 2, y1 - 5
    else:
        x1 += dimension.offset * SCALE
        x2 += dimension.offset * SCALE
        text_x, text_y = x1 + 7, (y1 + y2) / 2
    return f'<g class="dimension"><line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="#27322e" stroke-width="1" marker-start="url(#tick)" marker-end="url(#tick)"/><text x="{text_x:.1f}" y="{text_y:.1f}" font-family="Arial" font-size="9" fill="#27322e">{_esc(dimension.label)}</text></g>'


def _parking(plan: CandidatePlan) -> str:
    assert plan.parking is not None
    px = MARGIN + (plan.parking.x - plan.footprint.x) * SCALE
    py = MARGIN + (plan.parking.y - plan.footprint.y) * SCALE
    parts = [f'<g class="parking"><rect x="{px:.1f}" y="{py:.1f}" width="{plan.parking.width * SCALE:.1f}" height="{plan.parking.height * SCALE:.1f}" fill="#f7fbf8" stroke="#56615c" stroke-width="1.8"/>']
    for index in range(plan.parking.spaces):
        x = px + index * 10 * SCALE
        parts.append(f'<rect x="{x + 6:.1f}" y="{py + 8:.1f}" width="88" height="135" rx="10" fill="none" stroke="#56615c" stroke-width="1.2"/><text x="{x + 50:.1f}" y="{py + 78:.1f}" text-anchor="middle" font-family="Arial" font-size="9">CAR {index + 1}</text>')
    path_x = px + plan.parking.width * SCALE / 2
    parts.append(f'<path d="M{path_x:.1f},{py:.1f} L{path_x:.1f},{py - 24:.1f} L{_tx(plan.footprint.width / 2):.1f},{py - 24:.1f} L{_tx(plan.footprint.width / 2):.1f},{MARGIN:.1f}" stroke="#7a8580" stroke-width="1.2" stroke-dasharray="5 4"/><text x="{px:.1f}" y="{py - 8:.1f}" font-family="Arial" font-size="10" font-weight="700" fill="#43524d">PARKING</text></g>')
    return "".join(parts)


def _site_context(plan: CandidatePlan, floor: int) -> str:
    if floor != 1:
        return ""
    note = "CONCEPTUAL SITE ENVELOPE - EXACT SITE FIT NOT VERIFIED"
    if plan.site.exact_site_fit_verified:
        site_w = plan.site.conceptual_envelope.width * SCALE
        site_h = plan.site.conceptual_envelope.height * SCALE
        return f'<rect x="36" y="68" width="{site_w:.1f}" height="{site_h:.1f}" fill="none" stroke="#9aa39e" stroke-dasharray="8 5"/><text x="36" y="62" font-family="Arial" font-size="10" fill="#6a746f">SITE BOUNDARY</text>'
    return f'<text x="{MARGIN}" y="68" font-family="Arial" font-size="10" font-weight="700" fill="#9f3a38">{note}</text>'


def _north_arrow(x: float, y: float) -> str:
    return f'<g class="north"><text x="{x:.1f}" y="{y - 12:.1f}" text-anchor="middle" font-family="Arial" font-size="11" font-weight="700">N</text><path d="M{x:.1f},{y + 26:.1f} L{x:.1f},{y:.1f} M{x - 5:.1f},{y + 8:.1f} L{x:.1f},{y:.1f} L{x + 5:.1f},{y + 8:.1f}" stroke="#1d2522" fill="none" stroke-width="1.5"/></g>'


def _short_label(label: str) -> str:
    return label.upper().replace(" ROOM", "")


def _fit_label(label: str, room_width: float) -> str:
    max_chars = max(8, int(room_width * 1.15))
    if len(label) <= max_chars:
        return label
    replacements = {
        "MASTER BEDROOM": "MASTER BED",
        "MASTER BATHROOM": "MASTER BATH",
        "UTILITY / STORE": "UTILITY",
        "STORE / FLEX": "FLEX",
    }
    shortened = replacements.get(label, label)
    return shortened if len(shortened) <= max_chars else shortened[: max_chars - 1] + "."


def _feet_label(value: float) -> str:
    feet = int(value)
    inches = round((value - feet) * 12)
    if inches == 12:
        feet += 1
        inches = 0
    return f"{feet}'-{inches}\""


def _esc(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
