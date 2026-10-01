# Agent 4 Phase 2: grounded explanations

Phase 1 Python code owns candidate identity, eligibility, hard constraints, final
scores, rank order, budgets, planning outcomes and numeric comparisons. Phase 2
adds an optional explanation attachment to a copy of that result. It never writes
model output into deterministic decision fields or recalculates ranking.

## Use

Run from the backend Python environment:

```python
from app.agents.agent4_recommendation.agent import RecommendationAgent
from app.agents.agent4_recommendation.explanations import ExplanationService

decision = RecommendationAgent().recommend(context)  # no provider access
explained = ExplanationService().explain(context, decision)  # template fallback

# Explicit opt-in to the configured provider; this may incur provider charges.
service = ExplanationService.from_settings()
explained = service.explain(context, decision)
# Alternatively: service.recommend(context) computes Phase 1, then explains it.
```

The supplied context/decision pair is an internal application contract, not a
public endpoint accepting client-authored decisions. The integration must keep
them paired. Listing identity is checked against the context; this does not
cryptographically authenticate arbitrary caller-supplied decisions.

## Configuration and provider boundary

Reuse existing `LLM_PROVIDER` (`openai` or `gemini`), `LLM_MODEL`,
`OPENAI_API_KEY` and `GEMINI_API_KEY`. Keys come from project settings/environment,
never source code or evidence. Set a model supporting the provider's JSON-schema
output feature. Blank/unsupported configuration produces fallback; there is no
automatic model substitution. Existing settings load `.env` relative to the
working directory.

`ProviderConfig` contains validated limits: 20-second HTTP timeouts, 4,000 output
tokens and a 128,000-byte provider response limit. Limits are constructor-configurable
within hard bounds. HTTP timeouts bound individual I/O waits; the body-read loop
also checks elapsed time between chunks. This is not a hard process-wide deadline.
Endpoints are fixed; redirects and environment proxy inheritance are disabled.
No tools, database access, URL retrieval, file access or application actions are
supplied to the model. HTTP retries are not enabled.

OpenAI uses the Responses API with JSON Schema and `store=False`. Gemini uses
`generateContent` with JSON MIME type/schema. Provider keys are authentication
headers, never URL parameters. Errors are sanitized application codes; no provider
body, key, request object or exception detail is included in the recommendation.
The shared LLM stub is unchanged.

Provider references:
- [OpenAI structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
- [Gemini structured outputs](https://ai.google.dev/gemini-api/docs/structured-output)
- [Gemini generateContent](https://ai.google.dev/api/generate-content)

## Evidence and prompt

Prompt version: **propwise-agent4-explanation-v1**, defined in `prompts.py`.

The model may explain the supplied ranking, strengths, trade-offs, comparisons,
uncertainty, alternatives and next steps. It cannot invent properties or facts,
assert current availability, promise affordability, claim professional approval,
or describe preliminary construction estimates as quotations.

The evidence builder includes at most five recommendations and two alternatives.
It supplies confirmed structured requirements, deterministic decision fields,
criterion breakdowns, selected property facts, budgets, planning evidence,
assumptions, warnings, uncertainty, comparisons and coverage. Explanations cover
only this subset; the complete Phase 1 result is preserved.

Contact fields, addresses, artifact paths, provider settings and arbitrary state
are not selected. Obvious contact information, URLs, paths and secret-like strings
in excerpts are redacted. Short original-query and description excerpts are marked
untrusted and cannot be cited as factual proof. All upstream text, including text
inside warnings/requirements, remains data rather than instructions.

The serialized package is limited to 64,000 bytes. Excessive evidence triggers
fallback instead of dropping decision evidence to make a provider call. Individual
free-text values above 10,000 characters are refused. Excerpts and fallback display
text are bounded; any shortened fallback notices point back to the complete
deterministic evidence. Redaction is heuristic, not comprehensive personal-data
classification. Do not submit unnecessary personal data in requirements.

## Structured output and guardrails

`ExplanationDraft` requires an ordered identity/decision echo and grounded text
objects with evidence references. Validation proceeds as follows:

1. Bound output to 32,000 bytes; parse JSON, rejecting duplicate keys/nonfinite values.
2. Validate strict Pydantic types and reject extra fields.
3. Require exactly the selected candidate IDs/order and unchanged recommendation order.
4. Compare rank, final score, eligibility, budget status and planning-result echoes exactly.
5. Validate evidence references, candidate ownership and top-recommendation references.
6. Require factual/numeric prose to use `{{evidence.reference}}` placeholders.
   Literal numbers and common spelled-out numbers are rejected; Python inserts
   labelled values from the existing evidence. Requested values and raw descriptions
   are not citable property facts.
7. Reject obvious invented IDs, unknown facts presented as known, violations used
   as strengths, unsupported approval/availability/guarantee claims, instruction
   extraction, direct reordering claims and unrelated factual reference domains.
8. Render validated text and append deterministic warnings/notices, including
   assumptions, missing information, excluded costs, historical availability limits,
   conceptual-planning limitations and preliminary-estimate qualifications.

The model has no authority to suppress material warnings. Numeric labels/units
travel with the substituted values. Raw LLM JSON is not attached to the result.

These checks are conservative and can reject benign prose. They are **not a proof
of semantic entailment**: subtle factual implications, misleading phrasing,
cross-sentence reasoning and novel prompt injections still need human review and
evaluation. Schema compliance alone is not treated as factual correctness.
A field reference does not prove an upstream listing itself is true.

## Failure and fallback

`ExplanationService()` defaults to no provider. Phase 1 alone keeps
`explanation_status=DETERMINISTIC` and `explanation=None`.

With Phase 2, successful validated output uses `LLM`. Missing configuration,
transport failure, timeout, refusal, oversized/incomplete output, invalid JSON,
schema failure or guardrail failure produces `DETERMINISTIC_FALLBACK` with an
explicit reason and request-attempt count.

There is at most one synthesis request and, for invalid structured output, one
fresh repair request. Set `allow_repair=False` to disable repair. Repair includes
only a fixed validation error code and the same evidence, never raw rejected
output or exception text. Transport failures do not trigger repair.

Fallback provides a status summary, per-option deterministic reason/strengths/
trade-offs, warnings, comparisons, alternatives and next steps. Owned-land output
remains a plan assessment with no fabricated property ranking. Clarification and
empty-result responses also remain usable.

## Tests and scope

```text
python -B -m pytest -p no:cacheprovider tests/test_agent4.py tests/test_agent4_phase2.py -q
```

Phase 2 tests use fake providers and HTTPX MockTransport. An autouse fixture blocks
HTTPX's live HTTP transport. They test successful explanations, every fallback
path, bounded repair, exact decision preservation, identity/numeric integrity,
prompt injection, privacy filtering, missing evidence, provider payloads, refusals,
timeouts and size limits. Phase 1 tests are unchanged. No live smoke test is added;
no paid requests are part of this suite.

Live account access, selected-model compatibility, latency/cost and real-model
explanation quality have not been measured. No changes to Agents 1--3, ranking
formulas, shared LLM service, API/router, frontend or LangGraph are part of Phase 2.
