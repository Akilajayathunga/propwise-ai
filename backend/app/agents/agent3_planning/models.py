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

