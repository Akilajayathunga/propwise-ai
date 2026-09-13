from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.api.v1.router import router as api_v1_router
from app.config import settings


ROOT_DIR = Path(__file__).resolve().parents[2]
PLANS_DIR = ROOT_DIR / "storage" / "plans"
PLANS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title=settings.project_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_v1_router, prefix="/api/v1")
app.mount("/plans", StaticFiles(directory=PLANS_DIR), name="plans")
