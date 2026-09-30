from dataclasses import dataclass, field


@dataclass
class RoomRequirement:
    id: str
    type: str
    label: str
    required: bool
    priority: int
    preferred_area: float
    minimum_area: float
    floor_preference: int | None = None


@dataclass
class Rect:
    x: float
    y: float
    width: float
    height: float

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def top(self) -> float:
        return self.y + self.height


@dataclass
class Room:
    id: str
    type: str
    label: str
    floor_number: int
    x: float
    y: float
    width: float
    height: float
    area_sqft: float
    zone: str = "private"


@dataclass
class Wall:
    id: str
    floor_number: int
    wall_type: str
    x1: float
    y1: float
    x2: float
    y2: float
    thickness: float
    adjacent_spaces: list[str] = field(default_factory=list)


@dataclass
class Door:
    id: str
    floor_number: int
    connected_spaces: list[str]
    wall: str
    position: float
    width: float
    swing_direction: str
    door_type: str
    x: float
    y: float
    orientation: str


@dataclass
class Window:
    id: str
    floor_number: int
    room_id: str
    wall: str
    position: float
    width: float
    x: float
    y: float
    orientation: str


@dataclass
class Fixture:
    id: str
    floor_number: int
    room_id: str
    fixture_type: str
    x: float
    y: float
    width: float
    height: float
    label: str | None = None


@dataclass
class Dimension:
    id: str
    floor_number: int
    label: str
    x1: float
    y1: float
    x2: float
    y2: float
    offset: float
    dimension_type: str


@dataclass
class Parking:
    spaces: int
    x: float
    y: float
    width: float
    height: float


@dataclass
class SiteAnalysis:
    land_size_perches: float | None
    total_site_area_sqft: float | None
    width_ft: float | None
    length_ft: float | None
    exact_site_fit_verified: bool
    conceptual_envelope: Rect
    warnings: list[str] = field(default_factory=list)


@dataclass
class CandidatePlan:
    plan_id: str
    site: SiteAnalysis
    footprint: Rect
    floors: int
    rooms: list[Room]
    parking: Parking | None
    warnings: list[str] = field(default_factory=list)
    score: float | None = None
    score_breakdown: dict[str, float] = field(default_factory=dict)
    zones: dict[str, list[str]] = field(default_factory=dict)
    walls: list[Wall] = field(default_factory=list)
    doors: list[Door] = field(default_factory=list)
    windows: list[Window] = field(default_factory=list)
    fixtures: list[Fixture] = field(default_factory=list)
    dimensions: list[Dimension] = field(default_factory=list)
    circulation: dict[str, list[str]] = field(default_factory=dict)
    access_graph: dict[str, list[str]] = field(default_factory=dict)
    space_metrics: dict[str, float] = field(default_factory=dict)
    exterior_wall_thickness: float = 0.75
    interior_wall_thickness: float = 0.35
