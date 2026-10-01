import math

from app.agents.agent3_planning.models import Rect, SiteAnalysis
from app.schemas.planning import PlanningRequest, SelectedPropertyContext

PERCH_TO_SQFT = 272.25


def analyze_site(request: PlanningRequest, selected_property: SelectedPropertyContext | None) -> SiteAnalysis:
    warnings: list[str] = []
    land_size = request.land_size_perches or (selected_property.land_size_perches if selected_property else None)
    width = request.land_width_ft or (selected_property.land_width_ft if selected_property else None)
    length = request.land_length_ft or (selected_property.land_length_ft if selected_property else None)
    total_area = land_size * PERCH_TO_SQFT if land_size else None
    exact = bool(width and length)

    if exact and total_area:
        rectangular_area = width * length
        if abs(rectangular_area - total_area) / total_area > 0.15:
            warnings.append("Reported land area and plot dimensions differ materially; exact site fit is uncertain.")

    if not exact:
        warnings.append(
            "Land area is available, but exact plot dimensions are unavailable. "
            "The generated layout is conceptual and exact site fit cannot be confirmed."
        )

    if width and length:
        envelope = Rect(0, 0, width, length)
    elif total_area:
        width_guess = max(32.0, math.sqrt(total_area * 0.75))
        envelope = Rect(0, 0, width_guess, total_area / width_guess)
        warnings.append("A conceptual planning envelope was assumed from land area; it is not the real land shape.")
    else:
        envelope = Rect(0, 0, 50.0, 80.0)
        warnings.append("No land area was provided. A generic conceptual planning envelope was used.")

    return SiteAnalysis(land_size, total_area, width, length, exact, envelope, warnings)

