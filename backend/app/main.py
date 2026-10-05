from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from urllib.parse import parse_qs

from app.api.v1.router import router as api_v1_router
from app.config import settings


ROOT_DIR = Path(__file__).resolve().parents[2]
PLANS_DIR = ROOT_DIR / "storage" / "plans"
PLANS_DIR.mkdir(parents=True, exist_ok=True)


class PlanStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope: dict):
        response = await super().get_response(path, scope)
        filename = Path(path).name
        requested_download = parse_qs(scope.get("query_string", b"").decode("ascii", errors="ignore")).get("download") == ["1"]
        if response.status_code == 200 and (filename == "all_floor_plans.zip" or requested_download):
            if filename.isascii() and all(char.isalnum() or char in "_.-" for char in filename):
                response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


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
app.mount("/plans", PlanStaticFiles(directory=PLANS_DIR), name="plans")
