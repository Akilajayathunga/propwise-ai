from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Intent(str, Enum):
    BUY_PROPERTY = "BUY_PROPERTY"
    RENT_PROPERTY = "RENT_PROPERTY"
    BUY_LAND = "BUY_LAND"
    PLAN_HOUSE = "PLAN_HOUSE"
    LAND_AND_HOUSE = "LAND_AND_HOUSE"
    COMPARE_PROPERTIES = "COMPARE_PROPERTIES"
    ESTIMATE_BUDGET = "ESTIMATE_BUDGET"
    GENERAL_PROPERTY_QUERY = "GENERAL_PROPERTY_QUERY"
    UNKNOWN = "UNKNOWN"


class PropertyType(str, Enum):
    HOUSE = "house"
    APARTMENT = "apartment"
    LAND = "land"
    COMMERCIAL = "commercial"
    ROOM_ANNEX = "room_annex"
    OTHER = "other"


class ListingType(str, Enum):
    SALE = "sale"
    RENT = "rent"


class RequirementParseRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)

    @field_validator("query")
    @classmethod
    def query_must_have_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("query must not be blank")
        return cleaned


class ParsedRequirements(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    original_query: str
    intent: Intent = Intent.UNKNOWN
    location: str | None = None
    district: str | None = None
    minimum_budget_lkr: int | None = None
    maximum_budget_lkr: int | None = None
    maximum_land_budget_lkr: int | None = None
    total_project_budget_lkr: int | None = None
    construction_budget_lkr: int | None = None
    property_type: PropertyType | None = None
    listing_type: ListingType | None = None
    bedrooms: int | None = None
    bathrooms: int | None = None
    land_size_perches: float | None = None
    minimum_land_size_perches: float | None = None
    maximum_land_size_perches: float | None = None
    minimum_house_size_sqft: int | None = None
    floors: int | None = None
    parking_spaces: int | None = None
    preferred_style: str | None = None
    finish_level: str | None = None
    office_required: bool | None = None
    balcony_required: bool | None = None
    family_lounge_required: bool | None = None
    utility_room_required: bool | None = None
    preferences: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class Agent1Result(BaseModel):
    requirements: ParsedRequirements
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
