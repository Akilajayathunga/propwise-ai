# Agent 4 Phase 3: API and frontend integration

Phase 3 adds direct server-side orchestration and a vanilla JavaScript display.
Phase 1 scoring/eligibility and Phase 2 prompts/guardrails are unchanged.

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
`top_k` is an integer from 1 to 10. `explanation_enabled` is a boolean (API default:
true; browser checkbox default: false).

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
  (currently 30) ? Phase 1 ? optional Phase 2.
- Land + house: existing Agent 2 ? existing
  `app.api.v1.planning.evaluate_land_house` Python entry point once ? Phase 1 ?
  optional Phase 2. The existing cap of ten plans is preserved. Agent 4 does not
  estimate construction costs again.
- Owned land: existing Agent 3 requirement adapter ?
  `HomePlanningAgent.generate` once ? Phase 1 owned-land assessment ? optional
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
Final indices use ?84.2 / 100?, not a probability. All dynamic text uses
`textContent` or text-valued DOM properties; no dynamic model/listing HTML is inserted.
Existing static table markup remains static.

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
subset while the UI retains all deterministic candidates. Real browser visual,
artifact-download and live-model behavior still require the manual checks above.
The API is synchronous and conceptual planning may be slow. Existing legacy
endpoints remain available; this new recommendation endpoint does not trust their
outputs when supplied by a browser. No authentication redesign, database migration,
LangGraph or sensitivity analysis is included.
