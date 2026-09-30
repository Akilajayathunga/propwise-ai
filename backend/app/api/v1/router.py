from fastapi import APIRouter

from app.api.v1.planning import router as planning_router
from app.api.v1.property_search import router as property_search_router
from app.api.v1.requirements import router as requirements_router


router = APIRouter()
router.include_router(requirements_router)
router.include_router(property_search_router)
router.include_router(planning_router)


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "project": "PropWise AI"}
