from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.agents.agent3_planning.models import CandidatePlan


def render_png(plan: CandidatePlan, output_dir: Path) -> list[str]:
    paths: list[str] = []
    output_dir.mkdir(parents=True, exist_ok=True)
    for floor in range(1, plan.floors + 1):
        path = output_dir / ("ground_floor.png" if floor == 1 else f"floor_{floor}.png")
        _png_for_floor(plan, floor, path)
        paths.append(str(path))
    return paths


def _png_for_floor(plan: CandidatePlan, floor: int, path: Path) -> None:
    scale = 12
    margin = 48
    width = int(plan.footprint.width * scale + margin * 2)
    height = int(plan.footprint.height * scale + margin * 2)
    image = Image.new("RGB", (width, height), "#f8faf8")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    draw.text((margin, 16), ("Ground" if floor == 1 else f"Floor {floor}") + " - Conceptual Plan", fill="#1d2522", font=font)
    draw.rectangle((margin, margin, margin + plan.footprint.width * scale, margin + plan.footprint.height * scale), outline="#1d2522", width=3, fill="#ffffff")
    colors = ["#e7f3f4", "#f3efe7", "#edf4ea", "#f8ece8", "#ececf8"]
    rooms = [room for room in plan.rooms if room.floor_number == floor]
    for idx, room in enumerate(rooms):
        x = margin + room.x * scale
        y = margin + room.y * scale
        draw.rectangle((x, y, x + room.width * scale, y + room.height * scale), outline="#43524d", fill=colors[idx % len(colors)])
        draw.text((x + 5, y + 5), room.label[:24], fill="#1d2522", font=font)
        draw.text((x + 5, y + 19), f"{room.area_sqft:.0f} sqft", fill="#61706a", font=font)
    if floor == 1 and plan.parking:
        draw.rectangle((margin, height - 34, margin + plan.parking.width * scale, height - 12), outline="#43524d", fill="#dfe8ff")
        draw.text((margin + 5, height - 29), f"Parking x {plan.parking.spaces}", fill="#1d2522", font=font)
    image.save(path)

