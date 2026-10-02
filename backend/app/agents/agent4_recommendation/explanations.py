"""Optional Phase 2 wrapper. Ranking remains independently callable and unchanged."""
from app.agents.agent4_recommendation.agent import RecommendationAgent
from app.agents.agent4_recommendation.evidence import (
    EvidenceError, build_evidence, mandatory_notices, redact_text, selected_items,
)
from app.agents.agent4_recommendation.explanation_models import (
    ExplanationAttachment, ExplanationDraft, RenderedPropertyExplanation,
)
from app.agents.agent4_recommendation.guardrails import GuardrailError, parse_draft, render_text, validate_draft
from app.agents.agent4_recommendation.llm_client import ExplanationProvider, HTTPExplanationProvider, ProviderConfig, ProviderError
from app.agents.agent4_recommendation.prompts import PROMPT_VERSION, synthesis_prompt
from app.schemas.recommendation import RecommendationContext, RecommendationResponse


def fallback_text(value: str) -> str:
    return redact_text(value[:1200]) + (" [additional text omitted]" if len(value) > 1200 else "")


SUMMARY = {
    "OK": "The deterministic assessment is complete. Review the stated conditions and evidence limits before acting.",
    "NEEDS_CLARIFICATION": "More information is needed before a recommendation can be made.",
    "NO_SUITABLE_OPTION": "No supplied option satisfies the assessed requirements.",
    "INSUFFICIENT_EVIDENCE": "The supplied evidence is insufficient to confirm a suitable option.",
}


def deterministic_fallback(response: RecommendationResponse, reason: str, attempts: int = 0) -> ExplanationAttachment:
    items = selected_items(response)
    properties = []
    for item in items:
        detail = f"Eligibility: {item.eligibility.value}. Budget assessment: {item.budget.status}."
        if item.rank is not None:
            detail = f"Deterministic rank {item.rank}; decision-support index {item.final_recommendation_score:.2f}. " + detail
        else:
            detail += " This option is outside the recommendation shortlist."
        properties.append(RenderedPropertyExplanation(
            listing_id=item.listing_id, reason=detail,
            strengths=[fallback_text(s) for s in item.strengths],
            trade_offs=[fallback_text(s) for s in item.trade_offs + item.unmet_requirements + item.uncertainty],
            evidence_refs=[f"deterministic:{item.listing_id}"],
        ))
    next_steps = list(response.clarification_questions)
    if response.owned_land_assessment:
        next_steps.extend(response.owned_land_assessment.next_steps)
        next_steps.append("Review the supplied owned-land assessment and its planning limitations.")
    elif items:
        next_steps.append("Confirm missing facts, listing availability and any budget exclusions before committing.")
        if any(i.planning is not None for i in items):
            next_steps.append("Obtain professional review of site dimensions, conceptual plans and preliminary costs.")
    elif not next_steps:
        next_steps.append("Clarify requirements or retrieve additional candidates for assessment.")
    comparisons = []
    for comp in response.comparisons[:4]:
        text = f"{comp.first_listing_id} versus {comp.second_listing_id}: decision-support index difference {comp.score_difference:.2f}."
        if comp.expected_cost_difference_lkr is not None:
            text += f" Expected cost difference: {comp.expected_cost_difference_lkr:g} LKR ({comp.budget_basis})."
        comparisons.append(text)
    return ExplanationAttachment(
        prompt_version=PROMPT_VERSION, source="DETERMINISTIC_FALLBACK",
        fallback_reason=reason, attempts=attempts,
        summary=SUMMARY[response.status.value],
        top_recommendation_reason=properties[0].reason if response.recommendations else None,
        properties=properties, comparison_summary=comparisons,
        warnings=mandatory_notices(response),
        alternatives=[f"{i.listing_id}: {i.eligibility.value}; review unmet requirements and uncertainty."
                      for i in response.alternatives[:2]],
        next_steps=[fallback_text(s) for s in next_steps],
        explained_listing_ids=[i.listing_id for i in items],
    )


def render_explanation(draft, package, response, attempts):
    properties = []
    for item in draft.properties:
        statements = [item.reason] + item.strengths + item.trade_offs
        properties.append(RenderedPropertyExplanation(
            listing_id=item.listing_id, reason=render_text(item.reason, package),
            strengths=[render_text(s, package) for s in item.strengths],
            trade_offs=[render_text(s, package) for s in item.trade_offs],
            evidence_refs=list(dict.fromkeys(ref for s in statements for ref in s.evidence_refs)),
        ))
    fallback = deterministic_fallback(response, "NOT_USED")
    return ExplanationAttachment(
        prompt_version=PROMPT_VERSION, source="LLM", attempts=attempts,
        summary=render_text(draft.summary, package),
        top_recommendation_reason=render_text(draft.top_recommendation_reason, package) if draft.top_recommendation_reason else None,
        properties=properties,
        comparison_summary=[render_text(s, package) for s in draft.comparison_summary],
        warnings=list(dict.fromkeys(mandatory_notices(response) + [render_text(s, package) for s in draft.warnings])),
        alternatives=[render_text(s, package) for s in draft.alternatives],
        next_steps=[render_text(s, package) for s in draft.next_steps] or fallback.next_steps,
        explained_listing_ids=package.data["allowed_listing_ids"],
    )


class ExplanationService:
    """No provider is the safe default. Explicit from_settings() opts into a provider.

    explain() accepts an internal Phase 1 response, not client-supplied decisions.
    recommend() computes Phase 1 first for callers needing a single entry point.
    """
    def __init__(self, provider: ExplanationProvider | None = None, *, allow_repair: bool = True):
        self.provider = provider
        self.allow_repair = allow_repair

    @classmethod
    def from_settings(cls, settings=None, *, allow_repair=True):
        try:
            provider = HTTPExplanationProvider(ProviderConfig.from_settings(settings))
        except Exception:
            provider = None
        return cls(provider, allow_repair=allow_repair)

    def recommend(self, context: RecommendationContext) -> RecommendationResponse:
        return self.explain(context, RecommendationAgent().recommend(context))

    def explain(self, context: RecommendationContext, response: RecommendationResponse) -> RecommendationResponse:
        # A separate snapshot prevents provider activity from mutating the caller's decision.
        result = response.model_copy(deep=True)
        attempts = 0
        reason = "NOT_CONFIGURED"
        attachment = None
        try:
            if self.provider is not None and self.provider.configured:
                package = build_evidence(context, result)
                repair_code = None
                for _ in range(2 if self.allow_repair else 1):
                    attempts += 1
                    raw = self.provider.synthesize(synthesis_prompt(repair_code), package.json_text,
                                                   ExplanationDraft.model_json_schema())
                    try:
                        draft = parse_draft(raw)
                        validate_draft(draft, package)
                        attachment = render_explanation(draft, package, result, attempts)
                        break
                    except GuardrailError as exc:
                        # GuardrailError messages are fixed application codes.
                        reason = str(exc)
                        repair_code = reason
            if attachment is None:
                attachment = deterministic_fallback(result, reason, attempts)
        except EvidenceError as exc:
            safe_codes = {"EVIDENCE_TOO_LARGE", "TEXT_TOO_LARGE", "CONTEXT_ID_MISMATCH"}
            code = str(exc) if str(exc) in safe_codes else "EVIDENCE_UNAVAILABLE_OR_TOO_LARGE"
            attachment = deterministic_fallback(result, code, attempts)
        except ProviderError as exc:
            safe_codes = {"NOT_CONFIGURED", "PROVIDER_TIMEOUT", "PROVIDER_RESPONSE_TOO_LARGE",
                          "PROVIDER_HTTP_ERROR", "PROVIDER_INCOMPLETE", "PROVIDER_UNEXPECTED_OUTPUT",
                          "PROVIDER_REFUSAL", "PROVIDER_EMPTY", "PROVIDER_FAILURE"}
            code = str(exc) if str(exc) in safe_codes else "PROVIDER_FAILURE"
            attachment = deterministic_fallback(result, code, attempts)
        except TimeoutError:
            attachment = deterministic_fallback(result, "PROVIDER_TIMEOUT", attempts)
        except Exception:
            # Includes unexpected provider/mock exceptions. Never expose raw errors.
            attachment = deterministic_fallback(result, "EXPLANATION_FAILURE", attempts)
        result.explanation_status = attachment.source
        result.explanation = attachment
        return result
