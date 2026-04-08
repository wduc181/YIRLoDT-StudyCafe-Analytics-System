"""
cafe.py — Pydantic Schemas cho Cafe domain.

Ref: docs/api_design.md mục 5.4, 5.8, 5.9.
"""

from pydantic import BaseModel


class CafeResponse(BaseModel):
    """Response schema cho GET /api/cafes."""
    cafe_id: int
    name: str
    address: str | None = None
    center_lat: float
    center_lng: float
    radius_meters: int = 50
    behavior_score: float | None = None
    has_enough_data: bool = False

    model_config = {"from_attributes": True}


class CafeNearbyResponse(CafeResponse):
    """Response schema cho GET /api/cafes/nearby — kế thừa CafeResponse + distance."""
    distance_meters: float
    google_maps_url: str


class CafeCreate(BaseModel):
    """Request schema cho POST /api/cafes/suggest [Optional]."""
    device_id: str
    name: str
    address: str | None = None
    center_lat: float
    center_lng: float
    google_place_id: str | None = None
