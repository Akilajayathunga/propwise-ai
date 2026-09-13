from pathlib import Path

from app.agents.agent3_planning.models import CandidatePlan, Room


def render_svg(plan: CandidatePlan, output_dir: Path) -> list[str]:
    paths: list[str] = []
    output_dir.mkdir(parents=True, exist_ok=True)
    for floor in range(1, plan.floors + 1):
        floor_rooms = [room for room in plan.rooms if room.floor_number == floor]
        path = output_dir / ("ground_floor.svg" if floor == 1 else f"floor_{floor}.svg")
        path.write_text(_svg_for_floor(plan, floor, floor_rooms), encoding="utf-8")
        paths.append(str(path))
    return paths


def _svg_for_floor(plan: CandidatePlan, floor: int, rooms: list[Room]) -> str:
    scale = 8
    margin = 32
    width = int(plan.footprint.width * scale + margin * 2)
    height = int(plan.footprint.height * scale + margin * 2)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f8faf8"/>',
        f'<text x="{margin}" y="20" font-family="Arial" font-size="14" font-weight="700">{"Ground" if floor == 1 else "Floor " + str(floor)} - Conceptual Plan</text>',
        f'<rect x="{margin}" y="{margin}" width="{plan.footprint.width * scale}" height="{plan.footprint.height * scale}" fill="#ffffff" stroke="#1d2522" stroke-width="3"/>',
        f'<text x="{width - 58}" y="24" font-family="Arial" font-size="12">N ^</text>',
    ]
    colors = ["#e7f3f4", "#f3efe7", "#edf4ea", "#f8ece8", "#ececf8"]
    for idx, room in enumerate(rooms):
        x = margin + room.x * scale
        y = margin + room.y * scale
        w = room.width * scale
        h = room.height * scale
        parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{colors[idx % len(colors)]}" stroke="#43524d" stroke-width="1.5"/>')
        parts.append(f'<text x="{x + 5:.1f}" y="{y + 17:.1f}" font-family="Arial" font-size="10">{_esc(room.label)}</text>')
        parts.append(f'<text x="{x + 5:.1f}" y="{y + 31:.1f}" font-family="Arial" font-size="9">{room.area_sqft:.0f} sqft</text>')
    if floor == 1 and plan.parking:
        parts.append(f'<rect x="{margin}" y="{height - 28}" width="{plan.parking.width * scale:.1f}" height="18" fill="#dfe8ff" stroke="#43524d"/>')
        parts.append(f'<text x="{margin + 4}" y="{height - 14}" font-family="Arial" font-size="10">Parking x {plan.parking.spaces}</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def _esc(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

