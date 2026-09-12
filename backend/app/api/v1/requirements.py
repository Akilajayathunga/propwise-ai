from fastapi import APIRouter

from app.agents.agent1_requirements.agent import RequirementUnderstandingAgent
from app.schemas.requirements import ParsedRequirements, RequirementParseRequest


router = APIRouter(prefix="/requirements", tags=["requirements"])


@router.post("/parse", response_model=ParsedRequirements)
def parse_requirements(request: RequirementParseRequest) -> ParsedRequirements:
    result = RequirementUnderstandingAgent().parse(request.query)
    return result.requirements

