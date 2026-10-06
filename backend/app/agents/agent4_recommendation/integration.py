"""Thin server-side workflow. No internal HTTP, copied algorithms or plan retries."""
from app.agents.agent2_property.agent import PropertySearchAgent
from app.agents.agent3_planning.agent import HomePlanningAgent
from app.agents.agent3_planning.requirement_adapter import planning_request_from_requirements
from app.agents.agent4_recommendation.agent import RecommendationAgent, clarification_questions
from app.agents.agent4_recommendation.explanations import ExplanationService
from app.agents.agent4_recommendation.presentation import public_presentation
from app.schemas.planning import LandHouseEvaluationRequest, LandHouseEvaluationResponse, PlanningResponse
from app.schemas.property import Agent2Result
from app.schemas.recommendation import RecommendationContext, RecommendationResponse, ResponseStatus
from app.schemas.recommendation_api import RecommendationAPIResponse, RecommendationRequest


def existing_combined_evaluation(request):
    # The current combined public Python entry point lives in the planning route.
    # Lazy import avoids router cycles, reuses its ten-option cap and calls it once.
    from app.api.v1.planning import evaluate_land_house
    return evaluate_land_house(request)


def checked(model, value):
    return model.model_validate(value.model_dump() if hasattr(value, "model_dump") else value)


class RecommendationIntegration:
    def __init__(self, *, search=None, direct_plan=None, combined_plan=None, explanation_factory=None):
        self.search = search if search is not None else PropertySearchAgent().search
        self.direct_plan = direct_plan if direct_plan is not None else HomePlanningAgent().generate
        self.combined_plan = combined_plan if combined_plan is not None else existing_combined_evaluation
        self.explanation_factory = explanation_factory if explanation_factory is not None else ExplanationService.from_settings

    def run(self, request: RecommendationRequest) -> RecommendationAPIResponse:
        req = request.requirements.model_copy(deep=True)
        context = RecommendationContext(requirements=req, top_k=request.top_k)
        questions = clarification_questions(req)
        fields = []
        if req.intent == "PLAN_HOUSE":
            for name in ("land_size_perches", "bedrooms", "bathrooms", "floors"):
                if getattr(req, name) is None:
                    fields.append(name)
            for name in ("land_width_ft", "land_length_ft"):
                if request.owned_land is None or getattr(request.owned_land, name) is None:
                    fields.append("owned_land." + name)
            questions.extend("Provide " + field.replace("owned_land.", "").replace("_", " ") + "." for field in fields)
        if questions:
            decision = RecommendationResponse(status=ResponseStatus.NEEDS_CLARIFICATION,
                policy_version=RecommendationAgent().policy.version,
                clarification_questions=list(dict.fromkeys(questions)))
            return self._finish(request, context, decision, fields)

        failures = []
        if req.intent == "PLAN_HOUSE":
            planning_request = planning_request_from_requirements(req.model_copy(deep=True))
            planning_request.land_width_ft = request.owned_land.land_width_ft
            planning_request.land_length_ft = request.owned_land.land_length_ft
            planning_request.road_side = request.owned_land.road_side
            try:
                context.owned_land = checked(PlanningResponse, self.direct_plan(planning_request))
            except Exception:
                failures.append("Planning could not be completed or returned invalid evidence. No successful plan is assumed.")
        else:
            try:
                context.property_search = checked(Agent2Result,
                    self.search(req.model_copy(deep=True), top_n=PropertySearchAgent.TOP_N_DEFAULT))
            except Exception:
                failures.append("Property retrieval is unavailable or returned invalid evidence. Please try again.")
            if req.intent == "LAND_AND_HOUSE" and context.property_search and context.property_search.results:
                combined_request = LandHouseEvaluationRequest(requirements=req.model_copy(deep=True),
                    property_results=[p.model_dump() for p in context.property_search.results])
                try:
                    context.land_house = checked(LandHouseEvaluationResponse, self.combined_plan(combined_request))
                except Exception:
                    # The existing combined function is all-or-nothing on exception.
                    # Retain retrieved candidates as unassessed; never regenerate plans.
                    failures.append("Land-and-house planning was unavailable or incomplete. Retrieved candidates remain unassessed.")
        decision = RecommendationAgent().recommend(context)
        decision.warnings = list(dict.fromkeys(decision.warnings + failures))
        if context.land_house:
            decision.warnings = list(dict.fromkeys(decision.warnings + context.land_house.warnings))
            if context.land_house.cost_disclaimer:
                decision.warnings.append(context.land_house.cost_disclaimer)
        return self._finish(request, context, decision, fields)

    def _finish(self, request, context, decision, fields):
        if request.explanation_enabled:
            try:
                decision = self.explanation_factory().explain(context, decision)
            except Exception:
                # Also protect against integration/factory failure, without altering Phase 2.
                decision = ExplanationService().explain(context, decision)
        return RecommendationAPIResponse(**decision.model_dump(),
            presentation=public_presentation(context, decision), clarification_fields=fields)
