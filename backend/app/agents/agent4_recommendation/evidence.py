"""Bounded, allowlisted evidence. No contact fields, paths or provider settings."""
import json
import math
import re
from dataclasses import dataclass
from typing import Any

from app.schemas.recommendation import RecommendationContext, RecommendationResponse

MAX_RECOMMENDATIONS = 5
MAX_ALTERNATIVES = 2
MAX_EVIDENCE_BYTES = 64_000
AVAILABILITY_NOTICE = "Listing evidence may be historical; current availability is not verified."
CONSTRUCTION_NOTICE = "Construction costs are preliminary decision-support estimates, not quotations."
APPROVAL_NOTICE = "Conceptual planning is not architectural, structural, legal or professional site approval."
SCORE_NOTICE = "The final score is a decision-support index, not a probability or certainty percentage."


class EvidenceError(ValueError):
    pass


def redact_text(text: str) -> str:
    if len(text) > 10_000:
        raise EvidenceError("TEXT_TOO_LARGE")
    if "@" in text:
        text = re.sub(r"(?i)[\w.+-]+@[\w.-]+\.[a-z]{2,}", "[email omitted]", text)
    text = re.sub(r"(?i)https?://\S+|(?:[A-Z]:\\|/home/|/Users/)\S+", "[link/path omitted]", text)
    text = re.sub(r"(?<!\w)\+?\d[\d ()-]{7,}\d(?!\w)", "[contact-like text omitted]", text)
    text = re.sub(r"(?i)\b(?:sk-[a-z0-9_-]{8,}|AIza[a-z0-9_-]{10,})", "[secret-like text omitted]", text)
    return text


def safe_data(value: Any) -> Any:
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {k: v if k in {"listing_id", "first_listing_id", "second_listing_id"} else safe_data(v)
                for k, v in value.items()}
    if isinstance(value, list):
        return [safe_data(v) for v in value]
    return value


@dataclass(frozen=True)
class EvidencePackage:
    data: dict
    facts: dict
    json_text: str


def selected_items(response: RecommendationResponse):
    return response.recommendations[:MAX_RECOMMENDATIONS] + response.alternatives[:MAX_ALTERNATIVES]


def mandatory_notices(response: RecommendationResponse) -> list[str]:
    notices = [response.coverage.scope, SCORE_NOTICE]
    if response.recommendations or response.alternatives:
        notices.append(AVAILABILITY_NOTICE)
    notices.extend(response.warnings)
    for item in selected_items(response):
        notices.extend(f"{item.listing_id}: {value}" for value in item.warnings + item.unmet_requirements + item.uncertainty)
        if item.planning:
            notices.extend(f"{item.listing_id}: Assumption: {a}" for a in item.planning.assumptions)
            notices.extend([CONSTRUCTION_NOTICE, APPROVAL_NOTICE])
        if item.budget.construction is not None:
            notices.append(CONSTRUCTION_NOTICE)
        notices.extend(f"{item.listing_id}: Excluded cost: {cost}" for cost in item.budget.not_included)
    if response.owned_land_assessment:
        owned = response.owned_land_assessment
        notices.extend(owned.planning.warnings + owned.uncertainty + owned.unmet_requirements + owned.limitations)
        notices.extend("Assumption: " + a for a in owned.planning.assumptions)
        notices.extend([CONSTRUCTION_NOTICE, APPROVAL_NOTICE])
    return list(dict.fromkeys(redact_text(n[:1200]) + (" [additional text omitted; see deterministic evidence]" if len(n) > 1200 else "") for n in notices))


def build_evidence(context: RecommendationContext, response: RecommendationResponse,
                   max_bytes: int = MAX_EVIDENCE_BYTES) -> EvidencePackage:
    items = selected_items(response)
    originals = context.property_search.results if context.property_search else []
    counts = {}
    for prop in originals:
        counts[prop.listing_id] = counts.get(prop.listing_id, 0) + 1
    by_id = {p.listing_id: p for p in originals if counts[p.listing_id] == 1}
    if any(item.listing_id not in by_id for item in items):
        raise EvidenceError("CONTEXT_ID_MISMATCH")
    facts: dict[str, dict] = {}

    def register(prefix, value, owners=()):
        if isinstance(value, dict):
            for key, child in value.items():
                register(prefix + "." + key, child, owners)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                register(prefix + "." + str(index), child, owners)
        else:
            facts[prefix] = {"value": value, "owners": list(owners)}

    requirements = context.requirements.model_dump(mode="json", exclude={"original_query", "confidence", "missing_information"})
    coverage = response.coverage.model_dump(exclude={"excluded_ids", "unassessed_ids"})
    data = {"status": response.status.value, "policy_version": response.policy_version,
            "confirmed_requirements": safe_data(requirements),
            "allowed_listing_ids": [i.listing_id for i in items],
            "recommendation_order": [i.listing_id for i in response.recommendations[:MAX_RECOMMENDATIONS]],
            "coverage": coverage, "items": [], "owned_land": None,
            "comparisons": [], "required_notices": mandatory_notices(response),
            "untrusted_context": {"original_query_excerpt": redact_text(context.requirements.original_query)[:600],
                                  "listing_descriptions": []}}
    register("decision.status", data["status"])
    register("coverage", coverage)
    for index, item in enumerate(items):
        alias = "c" + str(index)
        source = by_id[item.listing_id]
        public = source.model_dump(include={"location", "district", "listing_type", "property_type",
            "bedrooms", "bathrooms", "land_size_perches", "house_size_sqft", "is_verified", "posted_date"})
        evidence = item.model_dump(mode="json", exclude={
            "title": True, "upstream_retrieval_score_breakdown": True,
            "criteria": {"__all__": {"explanation", "evidence_references"}},
            "constraint_checks": {"__all__": {"evidence"}},
        })
        # Source ad text is never citable proof of a factual assertion.
        evidence["known_property_facts"] = public
        evidence["role"] = "recommendation" if item in response.recommendations else "alternative"
        evidence = safe_data(evidence)
        data["items"].append({"alias": alias, **evidence})
        register(alias, evidence, [item.listing_id])
        data["untrusted_context"]["listing_descriptions"].append(
            {"listing_id": item.listing_id, "text": redact_text(source.description or "")[:400]})
    allowed = set(data["allowed_listing_ids"])
    for comp in response.comparisons:
        if {comp.first_listing_id, comp.second_listing_id} <= allowed:
            value = comp.model_dump()
            register("comparison." + str(len(data["comparisons"])), value,
                     [comp.first_listing_id, comp.second_listing_id])
            data["comparisons"].append(value)
    if response.owned_land_assessment:
        data["owned_land"] = safe_data(response.owned_land_assessment.model_dump(mode="json"))
        register("owned", data["owned_land"])
    register("clarifications", safe_data(response.clarification_questions))
    register("notice", data["required_notices"])
    data["facts"] = {ref: {"value": fact["value"]} for ref, fact in facts.items()}
    encoded = json.dumps(data, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    if len(encoded.encode("utf-8")) > max_bytes:
        # Keep the complete internal structure and owner-aware facts for validation.
        # Only the model-facing wire representation omits duplicate detail copies.
        wire = dict(data)
        wire["items"] = [
            {**{key: item[key] for key in ("alias", "role", "listing_id", "rank",
                                         "final_recommendation_score", "eligibility")},
             "budget": {"status": item["budget"]["status"]},
             "planning": {"constraints_satisfied": item["planning"]["constraints_satisfied"]}
                         if item["planning"] else None}
            for item in data["items"]
        ]
        # Every detailed scalar, including warnings/assumptions, remains citable
        # at exactly its original reference. Ownership stays in package.facts.
        wire["facts"] = {ref: fact["value"] for ref, fact in facts.items()}
        del wire["required_notices"]
        wire["required_notice_refs"] = [ref for ref in facts if ref.startswith("notice.")]
        encoded = json.dumps(wire, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    # Compaction is lossless, not truncation; legitimately oversized data fails.
    if len(encoded.encode("utf-8")) > max_bytes:
        raise EvidenceError("EVIDENCE_TOO_LARGE")
    return EvidencePackage(data=data, facts=facts, json_text=encoded)
