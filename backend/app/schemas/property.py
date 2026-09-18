from typing import Any

from pydantic import BaseModel, Field

from app.schemas.requirements import ParsedRequirements


class PropertyResult(BaseModel):
    """A single property listing returned by Agent 2, enriched with ranking signals."""

    listing_id: str
    title: str
    description: str | None = None
    district: str | None = None
    location: str | None = None
    address: str | None = None
    contact_number: str | None = None
    listing_type: str
    property_type: str
    price_lkr: float | None = None
    price_basis: str | None = None
    sale_total_price_lkr: float | None = None
    rent_monthly_lkr: float | None = None
    bedrooms: float | None = None
    bathrooms: float | None = None
    land_size_perches: float | None = None
    house_size_sqft: float | None = None
    property_size_sqft: float | None = None
    features: str | None = None
    is_verified: bool = False
    posted_date: str | None = None
    geo_region: str | None = None
    membership_level: str | None = None

    # Ranking metadata
    score: float = Field(ge=0.0, le=1.0, description="Composite relevance score (0–1)")
    score_breakdown: dict[str, float] = Field(
        default_factory=dict,
        description="Per-criterion score contributions for transparency",
    )


class PriceStats(BaseModel):
    """Descriptive price statistics across the filtered result set."""

    min_price: float | None = None
    max_price: float | None = None
    median_price: float | None = None
    mean_price: float | None = None
    count: int = 0


class Agent2Result(BaseModel):
    """Full output of Agent 2 – Property Search & Analysis."""

    results: list[PropertyResult] = Field(default_factory=list)
    total_found: int = Field(description="Total properties matching hard filters")
    returned: int = Field(description="Number of results in this response (≤ top_n)")
    relaxed_filters: bool = Field(
        default=False,
        description="True when hard filters were relaxed due to zero strict matches",
    )
    filters_applied: dict[str, Any] = Field(
        default_factory=dict,
        description="Snapshot of filter values that were actually applied",
    )
    analysis: dict[str, Any] = Field(
        default_factory=dict,
        description="Market analysis over the filtered set (price stats, district breakdown, etc.)",
    )
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PropertySearchRequest(BaseModel):
    """Request body for POST /api/v1/property-search."""

    requirements: ParsedRequirements
    top_n: int = Field(default=10, ge=1, le=50, description="Maximum results to return")
