"""Conservative validation of model prose, not a proof of semantic truth.

Decisions are compared exactly; factual values are rendered from labelled evidence.
Free-language entailment still requires human/evaluation review.
"""
import json
import re
import unicodedata

from pydantic import ValidationError

from app.agents.agent4_recommendation.evidence import EvidencePackage
from app.agents.agent4_recommendation.explanation_models import ExplanationDraft, GroundedText

MAX_DRAFT_BYTES = 32_000
PLACEHOLDER = re.compile(r"\{\{([a-zA-Z0-9_.]+)\}\}")
UNSAFE = re.compile(
    r"ignore.{0,40}(?:instructions|rules)|system\s*prompt|developer\s*message|"
    r"api[ _-]?key|provider\s*config|\bsecret\b|\bsk-[a-z0-9]|"
    r"\bAIza[a-z0-9]|reveal|execute|run\s+(?:command|shell)|"
    r"https?://|file://|<[^>]+>|\[[^]]*\]\(", re.I)
UNSUPPORTED = re.compile(
    r"guarantee|certainty|certainly|risk.free|currently\s+available|available\s+(?:now|today)|"
    r"\bapproved\b|construction.ready|structurally\s+(?:sound|safe)|legally\s+(?:safe|clear)|"
    r"\bquotation\b|\bquote\b|\bprobability\b|\bpercent\b|%", re.I)
PROMOTION = re.compile(r"\b(?:suitable|recommend(?:ed)?|affordable|feasible|confirmed|verified|successful)\b", re.I)
FACT_WORDS = re.compile(
    r"\b(?:price|cost|budget|margin|score|rank|bedrooms?|bathrooms?|floors?|parking|"
    r"location|district|pool|amenit(?:y|ies)|dimensions?|width|length|perches?|sqft)\b", re.I)
NUMBER_WORDS = re.compile(r"\b(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|million|billion)\b", re.I)
ORDER_CLAIM = re.compile(r"\b(?:first|second|third|best|prefer|choose|select|outperform|better|worse|higher|lower|cheaper|costlier)\b", re.I)
FACT_DOMAINS = {
    r"\b(?:pool|amenity|amenities)\b": (".strengths.", ".preferences."),
    r"\bbedrooms?\b": ("bedrooms",),
    r"\bbathrooms?\b": ("bathrooms",),
    r"\b(?:location|located|district)\b": ("location", "district"),
    r"\b(?:width|length|dimensions?)\b": ("width_ft", "length_ft", "exact_site_fit_verified"),
    r"\bprice\b": ("price_lkr",),
    r"\bscore\b": ("score", "contribution"),
    r"\brank\b": (".rank",),
}


class GuardrailError(ValueError):
    """Fixed code only; never include unsafe output text in errors."""


def _unique_object(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise GuardrailError("DUPLICATE_JSON_KEY")
        obj[key] = value
    return obj


def parse_draft(raw: str) -> ExplanationDraft:
    if not isinstance(raw, str) or len(raw.encode("utf-8")) > MAX_DRAFT_BYTES:
        raise GuardrailError("OUTPUT_SIZE")
    try:
        value = json.loads(raw, object_pairs_hook=_unique_object,
                           parse_constant=lambda _: (_ for _ in ()).throw(GuardrailError("NONFINITE_NUMBER")))
        return ExplanationDraft.model_validate(value)
    except GuardrailError:
        raise
    except (ValueError, TypeError, RecursionError, ValidationError):
        raise GuardrailError("INVALID_JSON_OR_SCHEMA") from None


def _check_listing_references(text: str, allowed_ids: list[str]) -> None:
    """Reject raw identities, not arbitrary words following listing/property.

    Placeholder barriers prevent an ID label from consuming the word after a
    grounded placeholder. Known IDs remain forbidden anywhere in free prose.
    Unknown references require explicit ID syntax or an identifier-shaped token;
    ordinary noun phrases are still subject to all other grounding checks.
    """
    plain = unicodedata.normalize("NFKC", PLACEHOLDER.sub("\x00", text))
    for listing_id in allowed_ids:
        value = unicodedata.normalize("NFKC", str(listing_id))
        if value and re.search(r"(?<![\w-])" + re.escape(value) + r"(?![\w-])", plain, re.I):
            raise GuardrailError("UNBOUND_LISTING_REFERENCE")
    explicit = r"\b(?:listing|property)\s+(?:id(?:entifier)?\b\s*[:=#]?\s*|[#\"'])\s*[\"']?[\w-]+"
    if re.search(explicit, plain, re.I):
        raise GuardrailError("UNBOUND_LISTING_REFERENCE")
    for match in re.finditer(r"\b(?:listing|property)\s+([\w-]+)", plain, re.I):
        token = match.group(1)
        if re.search(r"[\d_-]", token) or (token != "ID" and re.fullmatch(r"[A-Z]{2,}", token)):
            raise GuardrailError("UNBOUND_LISTING_REFERENCE")


def _check_text(statement: GroundedText, package: EvidencePackage, *,
                listing_id: str | None = None, section: str = "general") -> None:
    refs = statement.evidence_refs
    if len(set(refs)) != len(refs) or any(ref not in package.facts for ref in refs):
        raise GuardrailError("UNKNOWN_EVIDENCE")
    placeholders = PLACEHOLDER.findall(statement.text)
    if not set(placeholders) <= set(refs):
        raise GuardrailError("UNCITED_VALUE")
    plain = unicodedata.normalize("NFKC", PLACEHOLDER.sub("", statement.text))
    if "{{" in plain or "}}" in plain or any(unicodedata.category(c) == "Cf" for c in plain):
        raise GuardrailError("INVALID_PLACEHOLDER")
    if UNSAFE.search(plain) or UNSUPPORTED.search(plain) or ORDER_CLAIM.search(plain):
        raise GuardrailError("UNSAFE_OR_UNSUPPORTED_CLAIM")
    # Amounts, counts and decision numbers must be rendered from evidence, even
    # if a literal happens to equal a supplied number. This blocks cross-field swaps.
    if re.search(r"\d", plain) or NUMBER_WORDS.search(plain):
        raise GuardrailError("UNBOUND_NUMERIC_CLAIM")
    for ref in refs:
        fact = package.facts[ref]
        if listing_id is not None and fact["owners"] and fact["owners"] != [listing_id]:
            raise GuardrailError("CROSS_CANDIDATE_EVIDENCE")
        if isinstance(fact["value"], str) and UNSAFE.search(fact["value"]):
            raise GuardrailError("UNTRUSTED_INSTRUCTION_REFERENCE")
    if section == "comparison" and not any(ref.startswith("comparison.") for ref in refs):
        raise GuardrailError("UNSUPPORTED_COMPARISON")
    if section == "strength":
        if any(any(part in ref for part in (".uncertainty.", ".unmet_requirements.", ".warnings.")) or
               package.facts[ref]["value"] is None or
               (isinstance(package.facts[ref]["value"], str) and package.facts[ref]["value"] in
                {"UNKNOWN", "VIOLATED", "ABOVE_BUDGET", "HARD_CONSTRAINT_VIOLATION", "INSUFFICIENT_EVIDENCE"}) for ref in refs):
            raise GuardrailError("UNKNOWN_AS_STRENGTH")
    if any(package.facts[ref]["value"] is None for ref in refs):
        if not re.search(r"unknown|missing|unavailable|insufficient", plain, re.I):
            raise GuardrailError("MISSING_FACT_INVENTED")
    # Specific factual prose must actually insert the corresponding evidence.
    if FACT_WORDS.search(plain) and not placeholders:
        raise GuardrailError("UNBOUND_FACTUAL_CLAIM")
    for pattern, domains in FACT_DOMAINS.items():
        if re.search(pattern, plain, re.I) and not any(any(domain in ref for domain in domains) for ref in placeholders):
            raise GuardrailError("WRONG_FACT_DOMAIN")
    _check_listing_references(statement.text, package.data["allowed_listing_ids"])
    # Suitability is supplied in deterministic labels, never asserted by the LLM.
    # Conservative by design: even an apparently positive eligible claim must cite
    # the exact label via placeholder rather than paraphrase it as a guarantee.
    if PROMOTION.search(plain):
        raise GuardrailError("FEASIBILITY_CLAIM")
    # Do not use requested values as property facts: requirements aren't citable.
    # Raw descriptions/original text also never enter the facts registry.


def validate_draft(draft: ExplanationDraft, package: EvidencePackage) -> None:
    data = package.data
    if draft.recommendation_order != data["recommendation_order"]:
        raise GuardrailError("RANK_ORDER_CHANGED")
    expected = data["items"]
    if [p.listing_id for p in draft.properties] != [p["listing_id"] for p in expected]:
        raise GuardrailError("UNKNOWN_ID_OR_PROPERTY_ORDER")
    if bool(draft.top_recommendation_reason) != bool(data["recommendation_order"]):
        raise GuardrailError("TOP_RECOMMENDATION_MISMATCH")
    _check_text(draft.summary, package)
    if draft.top_recommendation_reason:
        _check_text(draft.top_recommendation_reason, package, listing_id=data["recommendation_order"][0])
    for explanation, item in zip(draft.properties, expected):
        wanted = (item["rank"], item["final_recommendation_score"], item["eligibility"],
                  item["budget"]["status"], item["planning"]["constraints_satisfied"] if item["planning"] else None)
        actual = (explanation.rank, explanation.final_score, explanation.eligibility,
                  explanation.budget_status, explanation.planning_constraints_satisfied)
        if actual != wanted:
            raise GuardrailError("DECISION_CHANGED")
        _check_text(explanation.reason, package, listing_id=explanation.listing_id)
        for text in explanation.strengths:
            _check_text(text, package, listing_id=explanation.listing_id, section="strength")
        for text in explanation.trade_offs:
            _check_text(text, package, listing_id=explanation.listing_id)
    for section in ("comparison_summary", "warnings", "alternatives", "next_steps"):
        for statement in getattr(draft, section):
            _check_text(statement, package, section="comparison" if section == "comparison_summary" else section)


def render_text(statement: GroundedText, package: EvidencePackage) -> str:
    def substitute(match):
        ref = match.group(1)
        value = package.facts[ref]["value"]
        if value is None:
            value = "unknown"
        elif type(value) is bool:
            value = "true" if value else "false"
        field = ref.rsplit(".", 1)[-1]
        if isinstance(value, str) and field in {"status", "eligibility", "evidence_status", "budget_status", "basis"}:
            value = {"OK": "recommendations ready", "HARD_CONSTRAINT_VIOLATION": "hard-constraint violation"}.get(
                value, value.replace("_", " ").lower())
        # Keep units meaningful without exposing the internal reference path.
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if field.endswith("_lkr"):
                return f"LKR {value:,.2f}".removesuffix(".00")
            if field.endswith("_sqft"):
                return f"{value:g} sq ft"
            if field.endswith("_ft"):
                return f"{value:g} ft"
            if field.endswith("_perches"):
                return f"{value:g} perches"
        return str(value)
    return PLACEHOLDER.sub(substitute, statement.text)
