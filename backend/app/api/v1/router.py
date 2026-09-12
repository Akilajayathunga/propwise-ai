from fastapi import APIRouter

from app.api.v1.requirements import router as requirements_router


router = APIRouter()
router.include_router(requirements_router)


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "project": "PropWise AI"}
