"""Public Agent 4 boundary: only user requirements, never trusted agent outputs."""
from fastapi import APIRouter, Depends, HTTPException

from app.agents.agent4_recommendation.integration import RecommendationIntegration
from app.schemas.recommendation_api import RecommendationAPIResponse, RecommendationRequest

router = APIRouter(prefix="/recommendation", tags=["recommendation"])


def get_recommendation_integration():
    return RecommendationIntegration()


@router.post("", response_model=RecommendationAPIResponse)
def recommend(request: RecommendationRequest,
              integration: RecommendationIntegration = Depends(get_recommendation_integration)):
    try:
        return integration.run(request)
    except Exception:
        # No provider keys, internal paths, exception text or tracebacks in HTTP output.
        raise HTTPException(status_code=500, detail="Recommendation processing failed. Please try again.") from None
