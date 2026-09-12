from fastapi import FastAPI

from app.api.v1.router import router as api_v1_router
from app.config import settings


app = FastAPI(title=settings.project_name)
app.include_router(api_v1_router, prefix="/api/v1")

