from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.agents.agent3_planning.models import CandidatePlan, Door, Fixture, Room, Window


SCALE = 14
MARGIN = 118


def render_png(plan: CandidatePlan, output_dir: Path) -> list[str]:
    paths: list[str] = []
    output_dir.mkdir(parents=True, exist_ok=True)
    for floor in range(1, plan.floors + 1):
        path = output_dir / ("ground_floor.png" if floor == 1 else f"floor_{floor}.png")
        _png_for_floor(plan, floor, path)
        paths.append(str(path))
    return paths


def _png_for_floor(plan: CandidatePlan, floor: int, path: Path) -> None:
    parking_extra = int((plan.parking.height + 9) * SCALE) if floor == 1 and plan.parking else 0
    width = int(plan.footprint.width * SCALE + MARGIN * 2 + 140)
    height = int(plan.footprint.height * SCALE + MARGIN * 2 + 105 + parking_extra)
    image = Image.new("RGB", (width, height), "#f6f5f1")
    draw = ImageDraw.Draw(image)
    fonts = _fonts()

    title = "GROUND FLOOR" if floor == 1 else f"FLOOR {floor}"
    draw.text((MARGIN, 28), f"{title} - CONCEPTUAL RESIDENTIAL PLAN", fill="#1d2522", font=fonts["title"])
    draw.text((MARGIN, 54), "Conceptual AI-assisted plan - not construction-ready", fill="#6a746f", font=fonts["small"])
    draw.text((width - 84, 24), "N", fill="#1d2522", font=fonts["bold"], anchor="mm")
    draw.line((width - 84, 72, width - 84, 38), fill="#1d2522", width=2)
    draw.line((width - 90, 48, width - 84, 38, width - 78, 48), fill="#1d2522", width=2)

    if floor == 1 and not plan.site.exact_site_fit_verified:
        draw.text((MARGIN, 72), "CONCEPTUAL SITE ENVELOPE - EXACT SITE FIT NOT VERIFIED", fill="#9f3a38", font=fonts["small_bold"])

    rooms = [room for room in plan.rooms if room.floor_number == floor]
    _draw_exterior(draw, plan)
    for room in rooms:
        if room.zone != "external":
            _draw_room_fill(draw, room)
    for room in rooms:
        _draw_partition(draw, room)
    for window in [item for item in plan.windows if item.floor_number == floor]:
        _draw_window(draw, window)
    for door in [item for item in plan.doors if item.floor_number == floor]:
        _draw_door(draw, door)
    for fixture in [item for item in plan.fixtures if item.floor_number == floor]:
        _draw_fixture(draw, fixture, fonts)
    for room in rooms:
        _draw_room_label(draw, room, fonts)
    _draw_dimensions(draw, plan, floor, fonts)
    if floor == 1 and plan.parking:
        _draw_parking(draw, plan, fonts)

    draw.text((MARGIN, height - 26), "Scale is conceptual. Verify all dimensions and approvals with qualified professionals.", fill="#6a746f", font=fonts["small"])
    image.save(path)


def _fonts() -> dict[str, ImageFont.ImageFont]:
    def truetype(name: str, size: int) -> ImageFont.ImageFont:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            return ImageFont.load_default()

    return {
        "title": truetype("arialbd.ttf", 18),
        "bold": truetype("arialbd.ttf", 12),
        "label": truetype("arialbd.ttf", 10),
        "regular": truetype("arial.ttf", 10),
        "small": truetype("arial.ttf", 9),
        "small_bold": truetype("arialbd.ttf", 9),
    }


def _tx(x: float) -> float:
    return MARGIN + x * SCALE


def _ty(y: float) -> float:
    return MARGIN + y * SCALE


def _draw_exterior(draw: ImageDraw.ImageDraw, plan: CandidatePlan) -> None:
    draw.rectangle((_tx(0), _ty(0), _tx(plan.footprint.width), _ty(plan.footprint.height)), outline="#111815", width=8)


def _draw_room_fill(draw: ImageDraw.ImageDraw, room: Room) -> None:
    fills = {
        "public": "#f7fbf8",
        "service": "#f8f7f0",
        "private": "#fbfaf7",
        "circulation": "#f0f3f1",
    }
    draw.rectangle((_tx(room.x), _ty(room.y), _tx(room.x + room.width), _ty(room.y + room.height)), fill=fills.get(room.zone, "#ffffff"))


def _draw_partition(draw: ImageDraw.ImageDraw, room: Room) -> None:
    color = "#3f4a45" if room.zone != "external" else "#62706a"
    draw.rectangle((_tx(room.x), _ty(room.y), _tx(room.x + room.width), _ty(room.y + room.height)), outline=color, width=2)


def _draw_door(draw: ImageDraw.ImageDraw, door: Door) -> None:
    x, y = _tx(door.x), _ty(door.y)
    w = door.width * SCALE
    erase = "#ffffff" if door.door_type == "main" else "#f6f5f1"
    if door.orientation == "vertical":
        draw.line((x, y - w / 2, x, y + w / 2), fill=erase, width=10)
        draw.line((x, y, x + w, y), fill="#222b27", width=2)
        draw.arc((x, y - w, x + w * 2, y + w), 180, 270, fill="#68736e", width=1)
    else:
        draw.line((x - w / 2, y, x + w / 2, y), fill=erase, width=10)
        draw.line((x, y, x, y + w), fill="#222b27", width=2)
        draw.arc((x - w, y, x + w, y + w * 2), 270, 360, fill="#68736e", width=1)


def _draw_window(draw: ImageDraw.ImageDraw, window: Window) -> None:
    x, y = _tx(window.x), _ty(window.y)
    w = window.width * SCALE
    if window.orientation == "vertical":
        draw.line((x, y - w / 2, x, y + w / 2), fill="#f6f5f1", width=10)
        draw.line((x - 4, y - w / 2, x - 4, y + w / 2), fill="#198da0", width=2)
        draw.line((x + 4, y - w / 2, x + 4, y + w / 2), fill="#198da0", width=2)
    else:
        draw.line((x - w / 2, y, x + w / 2, y), fill="#f6f5f1", width=10)
        draw.line((x - w / 2, y - 4, x + w / 2, y - 4), fill="#198da0", width=2)
        draw.line((x - w / 2, y + 4, x + w / 2, y + 4), fill="#198da0", width=2)


def _draw_fixture(draw: ImageDraw.ImageDraw, fixture: Fixture, fonts: dict[str, ImageFont.ImageFont]) -> None:
    x, y = _tx(fixture.x), _ty(fixture.y)
    w, h = fixture.width * SCALE, fixture.height * SCALE
    if fixture.fixture_type == "vehicle":
        draw.rounded_rectangle((x, y, x + w, y + h), radius=12, outline="#56615c", width=2)
        draw.text((x + w / 2, y + h / 2), fixture.label or "CAR", fill="#43524d", font=fonts["small_bold"], anchor="mm")
    elif fixture.fixture_type == "stair_treads":
        for index in range(1, 7):
            yy = y + h * index / 7
            draw.line((x, yy, x + w, yy), fill="#56615c", width=1)
        draw.text((x + w / 2, y + h / 2), fixture.label or "UP", fill="#1d2522", font=fonts["small_bold"], anchor="mm")
    elif fixture.fixture_type in {"bed", "counter", "sink", "cooker", "vehicle", "stair_treads"}:
        draw.rounded_rectangle((x, y, x + w, y + h), radius=3, outline="#7a8580", width=1)


def _draw_room_label(draw: ImageDraw.ImageDraw, room: Room, fonts: dict[str, ImageFont.ImageFont]) -> None:
    x = _tx(room.x + room.width / 2)
    y = _ty(room.y + room.height / 2)
    label = _fit_label(_short_label(room.label), room.width)
    box_w = min(room.width * SCALE - 10, max(72, len(label) * 7))
    box_h = 42
    draw.rounded_rectangle((x - box_w / 2, y - 24, x + box_w / 2, y + box_h / 2), radius=5, fill="#ffffff", outline="#d8ded8", width=1)
    draw.text((x, y - 12), label, fill="#1d2522", font=fonts["label"], anchor="mm")
    draw.text((x, y + 3), f"{_feet_label(room.width)} x {_feet_label(room.height)}", fill="#4f5b55", font=fonts["small"], anchor="mm")
    draw.text((x, y + 16), f"{room.area_sqft:.0f} sq.ft", fill="#6a746f", font=fonts["small"], anchor="mm")


def _draw_dimensions(draw: ImageDraw.ImageDraw, plan: CandidatePlan, floor: int, fonts: dict[str, ImageFont.ImageFont]) -> None:
    y = MARGIN - 10
    draw.line((_tx(0), y, _tx(plan.footprint.width), y), fill="#27322e", width=1)
    draw.text((_tx(plan.footprint.width / 2), y - 10), _feet_label(plan.footprint.width), fill="#27322e", font=fonts["small"], anchor="mm")
    x = _tx(plan.footprint.width) + 42
    draw.line((x, _ty(0), x, _ty(plan.footprint.height)), fill="#27322e", width=1)
    draw.text((x + 16, _ty(plan.footprint.height / 2)), _feet_label(plan.footprint.height), fill="#27322e", font=fonts["small"], anchor="mm")


def _draw_parking(draw: ImageDraw.ImageDraw, plan: CandidatePlan, fonts: dict[str, ImageFont.ImageFont]) -> None:
    assert plan.parking is not None
    px = MARGIN + (plan.parking.x - plan.footprint.x) * SCALE
    py = MARGIN + (plan.parking.y - plan.footprint.y) * SCALE
    draw.rectangle((px, py, px + plan.parking.width * SCALE, py + plan.parking.height * SCALE), outline="#56615c", fill="#f7fbf8", width=2)
    draw.text((px, py - 14), "PARKING", fill="#43524d", font=fonts["small_bold"])
    for index in range(plan.parking.spaces):
        car_x = px + index * 10 * SCALE + 8
        draw.rounded_rectangle((car_x, py + 12, car_x + 8.4 * SCALE, py + 14.0 * SCALE), radius=14, outline="#56615c", width=2)
        draw.text((car_x + 4.2 * SCALE, py + 7.2 * SCALE), f"CAR {index + 1}", fill="#43524d", font=fonts["small_bold"], anchor="mm")
    draw.line((px + plan.parking.width * SCALE / 2, py, px + plan.parking.width * SCALE / 2, py - 24, _tx(plan.footprint.width / 2), py - 24, _tx(plan.footprint.width / 2), _ty(0)), fill="#7a8580", width=1)


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
