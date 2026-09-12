from app.agents.agent1_requirements.extractor import extract_requirements
from app.agents.agent1_requirements.intent_classifier import classify_intent
from app.agents.agent1_requirements.validator import validate_requirements
from app.schemas.requirements import Agent1Result, ParsedRequirements
from app.services.llm_service import LLMService


class RequirementUnderstandingAgent:
    def __init__(self, llm_service: LLMService | None = None) -> None:
        self.llm_service = llm_service or LLMService()

    def parse(self, query: str) -> Agent1Result:
        cleaned_query = query.strip()
        intent = classify_intent(cleaned_query)
        extracted = extract_requirements(cleaned_query, intent)
        requirements = ParsedRequirements(
            original_query=cleaned_query,
            intent=intent,
            preferences=[],
            **extracted,
        )
        validated = validate_requirements(requirements)
        return Agent1Result(
            requirements=validated,
            metadata={
                "parser": "deterministic_fallback",
                "llm_configured": self.llm_service.is_configured(),
                "llm_used": False,
            },
        )

