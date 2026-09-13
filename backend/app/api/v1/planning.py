from fastapi import APIRouter

from app.agents.agent3_planning.agent import HomePlanningAgent
from app.schemas.planning import PlanningRequest, PlanningResponse

router = APIRouter(prefix="/planning", tags=["planning"])


@router.post("/generate", response_model=PlanningResponse)
def generate_plan(request: PlanningRequest) -> PlanningResponse:
    return HomePlanningAgent().generate(request)

