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

Accepted live configuration: **Gemini**, model **`gemini-3.1-flash-lite`**.
Gemini only synthesizes grounded explanations of the authoritative deterministic
result. It does not decide eligibility, budgets or ranking. OpenAI remains supported;
the recorded live acceptance results below concern Gemini, not live OpenAI testing.

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
`generateContent` with `generationConfig.responseFormat.text`,
`mimeType: "APPLICATION_JSON"` and a normalized schema; `candidateCount` is absent.
The Gemini-only wire-schema workaround removes string `minLength`/`maxLength`
constraints and the root `ExplanationDraft.properties` and `comparison_summary`
`maxItems` bounds. Other supported structure, including references, stays intact.
The original Pydantic models still enforce all limits locally. OpenAI receives its
original schema unchanged. This records the tested implementation, not a general
claim that Gemini rejects all array upper bounds.

Provider keys are authentication
headers, never URL parameters. Errors are sanitized application codes; no provider
body, key, request object or exception detail is included in the recommendation.
The shared LLM stub is unchanged.

Provider references:
- [OpenAI structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
- [Gemini structured outputs](https://ai.google.dev/gemini-api/docs/structured-output)
- [Gemini generateContent](https://ai.google.dev/api/generate-content)

## Evidence and prompt

Prompt version: **propwise-agent4-explanation-v5**, defined in `prompts.py`.
It preserves deterministic authority and candidate identities, requires exact
facts-key citations, and uses neutral grounded prose with land+house-specific
rules and fixed repair hints. No tools/actions are supplied.

Both `GroundedText.evidence_refs` and `{{...}}` placeholders must copy exact keys
from `facts`; paths elsewhere in requirements/items are not automatically citable.
A notice referenced by `required_notice_refs` is cited as `notice.N`, not the
array's index path. References cannot be invented, shortened or moved across
candidates. Missing information remains unknown. Land+house prose uses neutral
labels and placeholders, avoiding inferred feasibility, approval or availability
claims; optional prose may be omitted while all selected property entries remain.

The model may explain the supplied ranking, strengths, trade-offs, comparisons,
uncertainty, alternatives and next steps. It cannot invent properties or facts,
assert current availability, promise affordability, claim professional approval,
or describe preliminary construction estimates as quotations.

The evidence builder includes at most five recommendations and two alternatives.
It supplies confirmed structured requirements, deterministic decision fields,
criterion breakdowns, selected property facts, budgets, planning evidence,
assumptions, warnings, uncertainty, comparisons and coverage. Explanations cover
only this subset; the complete Phase 1 result is preserved.

`MAX_RECOMMENDATIONS = 5` and `MAX_ALTERNATIVES = 2` are **explanation-package
bounds only**. The public deterministic request independently accepts `top_k`
from 1 to 10. A response can retain 10 recommendations while the explanation covers
at most its first 5 recommendations + 2 alternatives. Two recommendations in a
particular example is an observed result, not a new limit.

Contact fields, addresses, artifact paths, provider settings and arbitrary state
are not selected. Obvious contact information, URLs, paths and secret-like strings
in excerpts are redacted. Short original-query and description excerpts are marked
untrusted and cannot be cited as factual proof. All upstream text, including text
inside warnings/requirements, remains data rather than instructions.

The serialized model-facing package is limited to **64,000 bytes**. Smaller
packages retain their existing representation. When the expanded package exceeds
that bound, only the wire representation is compacted: items retain identity and
decision echoes; detailed scalar facts remain under their original keys in `facts`.
Redundant `value` wrappers and duplicate notice strings are removed from the wire;
`required_notice_refs` points to the existing `notice.N` facts. The complete
internal structured evidence and owner-aware fact registry are unchanged.
Compaction removes duplicate representations, not authoritative facts or candidates.
If the compacted package still exceeds the limit, it fails safely before any
provider call. No unbounded payload or increased byte limit is used. Individual
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
   authoritative display values with applicable units from the existing evidence. Requested values and raw descriptions
   are not citable property facts.
7. Reject obvious invented IDs, unknown facts presented as known, violations used
   as strengths, unsupported approval/availability/guarantee claims, instruction
   extraction, direct reordering claims and unrelated factual reference domains.
8. Render validated text and append deterministic warnings/notices, including
   assumptions, missing information, excluded costs, historical availability limits,
   conceptual-planning limitations and preliminary-estimate qualifications.

The model has no authority to suppress material warnings. Numeric labels/units
travel with the substituted values. Rendered prose hides internal paths such as
`c0.*` and humanizes status/eligibility values; structured evidence references and
enums remain intact. Raw LLM JSON is not attached to the result.
Prompt injection cannot change ranking because model output is never used to
write deterministic decision fields. This separation is distinct from guaranteeing
perfect detection of every possible malicious or misleading sentence.

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
only a fixed validation error code, application-authored repair guidance and the
same evidence, never raw rejected output or arbitrary exception text. Transport failures do not trigger repair.

Fallback provides a status summary, per-option deterministic reason/strengths/
trade-offs, warnings, comparisons, alternatives and next steps. Owned-land output
remains a plan assessment with no fabricated property ranking. Clarification and
empty-result responses also remain usable.
Fallback prose humanizes enum labels: for example,
`Eligibility: hard-constraint violation. Budget assessment: within budget.`
Alternatives and comparison budget-basis labels are humanized too. Structured
`eligibility`, budget status and response status remain unchanged.

Evidence failures expose only the whitelisted codes `EVIDENCE_TOO_LARGE`,
`TEXT_TOO_LARGE` and `CONTEXT_ID_MISMATCH`; unknown evidence errors map to
`EVIDENCE_UNAVAILABLE_OR_TOO_LARGE`. They cause zero provider attempts. Provider
HTTP diagnostics retain sanitized status/category internally; public fallback
remains generic and does not expose request/response bodies, credentials or paths.

## Tests and scope

```text
python -B -m pytest -p no:cacheprovider tests/test_agent4.py tests/test_agent4_phase2.py tests/test_agent4_phase3.py -q
```

Phase 2 tests use fake providers and HTTPX MockTransport. An autouse fixture blocks
HTTPX's live HTTP transport. They test successful explanations, every fallback
path, bounded repair, exact decision preservation, identity/numeric integrity,
prompt injection, privacy filtering, missing evidence, provider payloads, refusals,
timeouts and size limits. Phase 1 tests are unchanged. No live smoke test is added;
no paid requests are part of this suite.

The accepted test snapshot is **305 Agent 4 Phase 1-3 tests passing** and
**398 full backend tests passing**, with no failures. See the
[final acceptance record](agent4-phase3.md#final-acceptance-snapshot-2026-10-03)
for warning details, reproducible scenario measurements and live results.
Controlled Gemini tests verified both Kandy property and Kottawa land+house
explanations with `source=LLM`, `fallback_reason=null`, `attempts=1`.
These observed successes do not guarantee every future request or provider uptime;
latency/cost benchmarking and broad semantic-quality evaluation remain separate.
Agents 1-3 algorithms, deterministic ranking, and the shared LLM stub remain
unchanged by this explanation layer. API/frontend integration is documented in
Phase 3; LangGraph is not used.
