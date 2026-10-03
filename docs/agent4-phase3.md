# Agent 4 Phase 3: API and frontend integration

Phase 3 adds direct server-side orchestration and a vanilla JavaScript display.
It invokes Phase 1 and the current Phase 2 layer without moving their logic into
the router or browser. The accepted explanation layer uses Prompt v5; see
[Phase 2](agent4-phase2.md) for provider, evidence and guardrail details.

## Public API

`POST /api/v1/recommendation`

Example property request (explicitly disables provider calls):

```json
{
  "requirements": {
    "original_query": "Buy a three-bedroom house in Kandy under LKR 30 million",
    "intent": "BUY_PROPERTY",
    "listing_type": "sale",
    "property_type": "house",
    "location": "Kandy",
    "maximum_budget_lkr": 30000000,
    "bedrooms": 3
  },
  "top_k": 3,
  "explanation_enabled": false
}
```

`requirements` is the confirmed Agent 1 schema with extra fields forbidden and
public input bounds. These are user requirements, not evidence that any property
satisfies them. Parser confidence/missing-information fields remain informational.
`top_k` is an integer from 1 to 10 (API default 3; browser sends 10).
`explanation_enabled` is a boolean (API default true; browser checkbox default false).
The deterministic response is independent of the explanation-only bound of
5 recommendations + 2 alternatives. The browser retains all deterministic
recommendations and alternatives even when only a subset is explained.

For `PLAN_HOUSE`, also submit:

```json
{
  "owned_land": {
    "land_width_ft": 50,
    "land_length_ft": 80,
    "road_side": "north"
  }
}
```

Area, bedrooms, bathrooms, floors and construction/total budget belong in
`requirements`. Missing required owned-land inputs return `NEEDS_CLARIFICATION`
before planning is invoked. Width/length must be positive and at most 10,000 feet.
Dimensions are never invented by the integration. Owned-land input on another
workflow is rejected.

Neither the request nor its nested requirements/site input accepts prices of
candidate properties, ranking scores, eligibility, selected-property evidence,
Agent2Result, PlanningResponse, LandHouseEvaluationResponse or RecommendationResponse.
Unsupported intents, extra fields and invalid types/ranges return 422.

The response extends the complete `RecommendationResponse` with:

- `clarification_fields`: structured missing owned-land field names.
- `presentation.properties`: server-retrieved listing details for assessed IDs.
- `presentation.retrieval`: counts, relaxed-filter flag, warnings, filters,
  analysis and documented metadata.
- `presentation.land_house_options`: assessed option details and safe artifact URLs.
- `presentation.owned_plan`: existing direct planning output with safe artifact URLs.

`OK`, `NEEDS_CLARIFICATION`, `NO_SUITABLE_OPTION` and
`INSUFFICIENT_EVIDENCE` are normal decision responses (HTTP 200).
Unexpected orchestration errors return a generic HTTP 500 without exception text.
Upstream failure details are replaced by stage-specific warnings, not raw errors.

## Execution

- Purchase/rental/land purchase/comparison: existing
  `PropertySearchAgent.search(..., top_n=PropertySearchAgent.TOP_N_DEFAULT)`
  (currently 100) -> Phase 1 -> optional Phase 2.
- Land + house: existing Agent 2 -> existing
  `app.api.v1.planning.evaluate_land_house` Python entry point once -> Phase 1 ->
  optional Phase 2. The existing cap of ten plans is preserved. Agent 4 does not
  estimate construction costs again.
- Owned land: existing Agent 3 requirement adapter ->
  `HomePlanningAgent.generate` once -> Phase 1 owned-land assessment -> optional
  Phase 2. No fabricated property ranking.
- Agent 1 parsing remains the existing separate request, followed by user answers
  in the browser. The new endpoint accepts confirmed requirements.

Complete upstream responses stay in the server's internal RecommendationContext.
Warnings/metadata are not discarded before Agent 4. Public metadata is projected;
provider configuration and arbitrary internal metadata are not returned.
Display objects never influence the rank order.

If combined evaluation throws, its current all-or-nothing function cannot return
already processed options. The integration does not retry or duplicate generation:
it retains retrieval evidence, reports planning as unavailable/incomplete and
marks candidates unassessed. Mixed successful/failed options returned normally are
handled by existing Phase 1 eligibility. Files written before an upstream exception
may remain in storage; cleanup/refactoring of Agent 3 is outside this phase.

Explanations use the existing configured ExplanationService. Disabled means no
provider construction/call. Enabled means validated LLM output or the existing
deterministic fallback. No provider availability changes scores or rank order.

## Browser integration and safe rendering

The browser still parses the initial query through Agent 1 and uses the existing
follow-up mechanism. It now also asks for missing budget and measured owned-land
dimensions. It submits one recommendation request, containing only user input.
It no longer posts property results to the planning endpoint.

The Agent 4 panel shows final ranks, decision-support indices, eligibility,
criterion contributions, budgets, strengths, trade-offs, unmet requirements,
uncertainty, warnings, comparisons, explanation source and candidate coverage.
Owned-land results remain assessments. Other candidates are explicitly labelled
as alternatives/outside the shortlist, including violations and missing evidence.

Existing ad dialogs, budget summaries, floor previews and downloads are reused.
Upstream scores are labelled as upstream evidence, never the final recommendation.
Final indices use `84.2 / 100`, not a probability. All dynamic text uses
`textContent` or text-valued DOM properties; no dynamic model/listing HTML is inserted.
Existing static table markup remains static. Both validated LLM output and
deterministic fallback display human-readable enums; structured API values remain
unchanged. Internal evidence paths are not displayed as prose. An unmet location
label is shown as `Does not match the requested location: Kandy`; satisfied
strengths are not rewritten as failures.

Artifact paths are resolved under the configured server plans directory and
projected as restricted `/plans/plan-.../filename.ext` paths. Traversal, external
URLs and unsupported file extensions are rejected. The frontend accepts only those
relative artifact URLs on its configured backend origin.

## Automated tests

From `backend`:

```text
python -B -m pytest -p no:cacheprovider tests/test_agent4.py tests/test_agent4_phase2.py tests/test_agent4_phase3.py -q
```

Phase 3 tests use fake upstream results and fake providers. HTTPX live transport is
blocked and the provider factory is replaced independently of real API keys.
One test exercises the existing combined evaluator with mocked plan generation,
verifying its ten-option cap and one generation per option. Any planning storage
root used by tests is redirected to temporary directories.

Frontend validation also used JavaScript syntax checks and a lightweight mock-DOM/
mock-fetch smoke run covering the single endpoint, budget/dimension follow-ups,
literal injection-like text, index labels and restricted artifact URLs. This is
not a substitute for browser layout and download testing.

## Final acceptance snapshot (2026-10-03)

**Overall: READY FOR FINAL DEMO.** These are recorded acceptance results, not a
claim that tests or live calls were rerun during documentation cleanup.

| Suite/check | Result |
| --- | --- |
| Agent 4 Phase 1-3 | 305 passed, 0 failed, 0 skipped |
| Full backend | 398 passed, 0 failed, 0 skipped |
| `frontend/app.js` and `frontend/agent4.js` | JavaScript syntax passed using V8 compilation |
| Fallback presentation smoke check | PASS; no raw enum labels in the reproduced Kandy UI |

The two existing dependency/setup warnings concern Pydantic's `PlanFileSet.json`
name and Starlette's TestClient/httpx deprecation. In the full-suite run one warning
appeared during setup and one in pytest's summary. They are not Agent 4 failures.
The Agent 4 suite is included in the full backend total; do not add the totals.
Automated tests used mocks/offline transport. Full-backend planning artifacts were
redirected to temporary storage and removed. No live provider calls ran in pytest.

| Acceptance area | Result |
| --- | --- |
| Buy-property | PASS |
| No-suitable-option | PASS |
| Land+house | PASS |
| Impossible request | PASS |
| Owned-land | PASS |
| Explanation disabled | PASS |
| Provider fallback | PASS |
| Deterministic authority | PASS |
| Candidate-count behavior | PASS |
| Security regression | PASS |
| Presentation | PASS |
| API/integration | PASS |

The OFF/ON checks compared all deterministic response fields, including IDs, order,
ranks, scores, eligibility, budgets, planning evidence and coverage. Disabled
explanations construct/call no provider. Timeout, 429/503, malformed/schema-invalid
output and guardrail failures preserve the usable deterministic result. Public
input rejects fabricated trusted agent evidence; integration calls existing Python
entry points directly, preserves planning limits and does not generate plans twice.
Owned-land assessment and uncertainty were exercised with fixtures; contradictory
owned-land area/dimensions have no dedicated acceptance fixture and were not
independently verified. Visual browser layout/download testing is separate from
syntax and in-memory DOM checks.

### Controlled live Gemini verification

Provider: **Gemini**; model: **`gemini-3.1-flash-lite`**; prompt:
**`propwise-agent4-explanation-v5`**. No credentials or environment-file contents
are included here. The LLM only explained deterministic results.

| Scenario | `explanation_status` / source | `fallback_reason` | Attempts |
| --- | --- | --- | --- |
| Kandy property | `LLM` | `null` | 1 |
| Kottawa land+house | `LLM` | `null` | 1 |

Kandy request: "I want to buy a 3 bedroom house in Kandy under 30 million LKR".
Its deterministic status was `NO_SUITABLE_OPTION`: no recommendation, with the
retrieved property retained as an alternative due to the original location
constraint. `LLM` means the explanation passed validation, not that a property
became suitable.

Kottawa request: "I have a total budget of 40 million LKR. I want to buy land in
Kottawa and build a 3 bedroom house with 2 bathrooms and 2 floors."

| Kottawa measurement | Recorded result |
| --- | --- |
| Matching / retrieved candidates | 106 / 8 |
| Planning-assessed candidates | 8 |
| Deterministic result | 2 recommendations + 6 alternatives |
| LLM explanation subset | 2 recommendations + 2 alternatives |
| Expanded evidence (before compaction) | 103,674 bytes |
| Compacted model-facing evidence | 58,453 bytes |
| Evidence limit | 64,000 bytes |
| Authoritative scalar facts preserved | 776 |

Retrieval coverage was limited; planning covered all retrieved candidates in this
case. Total-project affordability used land cost plus preliminary construction
low/expected/high ranges, project ranges, expected margin, assumptions, excluded
costs and site limitations. The two recommendations were the deterministic outcome,
not a lowered limit: compaction preserved all facts/references/owners and did not
reduce the response. A separate acceptance case retained 10 deterministic
recommendations while explaining at most 5 recommendations + 2 alternatives.
Counts depend on the dataset and request; these are measured examples, not promises
for every environment. Live HTTP success was followed by strict Pydantic and
unchanged guardrail validation. Future provider failures still fall back safely.

## Manual browser checklist (no paid calls)

1. Start the backend from `backend` using `python -m uvicorn app.main:app --reload`.
   Serve `frontend` with `python -m http.server 3000`; open localhost:3000.
2. Leave **Use grounded AI explanations** unchecked. In DevTools, confirm
   `explanation_enabled:false` in the recommendation request.
3. Submit purchase and rental queries. Confirm monthly rent is separate from sale
   price, final indices use /100, original constraints remain visible and details
   open correctly. Compare final order with upstream relevance in the details.
4. Submit land purchase and land + house queries. Answer budget/room follow-ups.
   Confirm only one recommendation POST follows parsing; the browser does not
   post trusted candidates or call planning separately.
5. Inspect land/construction/project ranges, layout failures, site uncertainty and
   excluded costs. Open plan previews and budget CSV/report/download controls.
6. For owned land, omit dimensions initially. Confirm width/length are requested
   before generation. Complete them and check assessment, limitations and artifacts.
7. Try impossible budgets/no matches, missing evidence and relaxed retrieval.
   Confirm statuses, warning lists, alternatives and coverage remain visible.
8. Test backend-offline and HTTP 422/500 cases; confirm a readable error and that
   the submit button becomes usable again.
9. Inspect narrow/mobile layout, keyboard access to details/dialogs and long text.
   Confirm injection-like listing/model text is displayed literally.
10. To test fallback without a provider, use an environment with no provider key/model,
    then check the AI explanation option. Do not enable this against configured
    credentials until separately approving a live provider test.

## Remaining limits

Historical data and upstream retrieval truncation remain unchanged. Land-and-house
planning covers at most ten upstream-selected options. Phase 2 explains its bounded
subset while the UI retains all deterministic candidates. The recorded live
Kandy/Kottawa cases passed; this is not a guarantee of future model responses or
provider availability. Browser visual/layout and artifact-download checks remain
separate manual checks.
The API is synchronous and conceptual planning may be slow. Existing legacy
endpoints remain available; this new recommendation endpoint does not trust their
outputs when supplied by a browser. No authentication redesign, database migration,
LangGraph or sensitivity analysis is included.
