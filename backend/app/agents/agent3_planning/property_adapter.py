from typing import Any

from app.schemas.planning import SelectedPropertyContext
from app.schemas.property import PropertyResult


def adapt_selected_property(value: Any) -> SelectedPropertyContext | None:
    if value is None:
        return None

    data = value.model_dump() if hasattr(value, "model_dump") else dict(value)

    return SelectedPropertyContext(
        listing_id=data.get("listing_id"),
        location=data.get("location"),
        district=data.get("district"),
        property_type=data.get("property_type"),
        land_size_perches=data.get("land_size_perches"),
        land_price_lkr=data.get("land_price_lkr") or data.get("sale_total_price_lkr") or data.get("price_lkr"),
        land_width_ft=data.get("land_width_ft"),
        land_length_ft=data.get("land_length_ft"),
        road_side=data.get("road_side"),
        source_score=data.get("source_score") or data.get("score"),
    )


def adapt_property_result(result: PropertyResult) -> SelectedPropertyContext:
    return adapt_selected_property(result) or SelectedPropertyContext()

