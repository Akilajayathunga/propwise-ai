from fastapi import APIRouter

from app.agents.agent2_property.agent import PropertySearchAgent
from app.schemas.property import Agent2Result, PropertySearchRequest

router = APIRouter(prefix="/property-search", tags=["property-search"])


@router.post("", response_model=Agent2Result)
def search_properties(request: PropertySearchRequest) -> Agent2Result:
    """Execute Agent 2: Property Search & Analysis based on structured requirements."""
    agent = PropertySearchAgent()
    return agent.search(request.requirements, top_n=request.top_n)

