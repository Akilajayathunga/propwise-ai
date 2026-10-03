# Architecture

## Current Agent 4 Architecture

The implemented demo uses vanilla HTML/CSS/JavaScript and FastAPI. Agent 1 parses
requirements; after confirmation, `POST /api/v1/recommendation` invokes existing
upstream Python entry points directly. There is no internal HTTP round-trip or
LangGraph orchestration in this flow.

- Property search: Agent 1 -> Agent 2 -> Agent 4.
- Owned-land planning: Agent 1 -> Agent 3 -> Agent 4.
- Land + house: Agent 1 -> Agent 2 -> Agent 3 -> Agent 4.

Agent 4 receives structured requirements and server-obtained retrieval/planning
evidence. Deterministic Python owns original hard-constraint checks, eligibility,
budget assessment, final decision-support scores and ranking, alternatives,
comparisons, coverage and owned-land assessment. An owned-land assessment does not
fabricate a property ranking. Scores are indices, not probabilities.

Agent 2's existing relevance score/order is upstream evidence, not the final
recommendation. Its full score and Agent 3's combination score are not added as
weighted criteria in Agent 4, avoiding double-counting. Retrieval relevance may
break ties. Individual budget, layout, site-fit, assumption and warning evidence
is assessed separately; upstream algorithms remain unchanged.

```text
Confirmed requirements -> upstream retrieval/planning -> deterministic Agent 4
    -> bounded allowlisted evidence -> optional LLM synthesis
    -> strict Pydantic validation -> grounding/authority guardrails
    -> grounded explanation OR usable deterministic fallback
```

The LLM cannot change candidate identity, recommendation order, rank, score,
eligibility, budget or planning outcomes. It has no tools/actions. The accepted
Gemini model is `gemini-3.1-flash-lite`, with Prompt v5. The public API accepts
user-controlled requirements, not fabricated agent evidence.

The API's deterministic `top_k` is 1-10 (default 3; the browser requests 10).
The independent explanation bound is at most 5 recommendations + 2 alternatives,
within 64,000 bytes. It never reduces the deterministic response. See
[Phase 2](agent4-phase2.md) for grounding/compaction and
[Phase 3](agent4-phase3.md) for integration and final acceptance evidence.

## Historical Foundation Plan

The original proposed request flow is retained below. It is not the current demo
implementation:

```text
User
↓
Next.js
↓
FastAPI
↓
LangGraph
↓
Agent 1
↓
Agent 2
↓
Agent 3
↓
Agent 4
↓
Final Result
```

### Originally Planned Components

- Frontend: Next.js with TypeScript.
- Backend: Python with FastAPI.
- Agent orchestration: LangGraph.
- Database: Supabase PostgreSQL.
- Vector search: Supabase pgvector.
- Authentication: Supabase Auth.
- Authorization: Supabase Row Level Security.
- CAD generation: Python with ezdxf.
- LLM access: OpenAI or Gemini through a provider abstraction.

### Conditional Routes in the Original Plan

- Property search: Agent 1 → Agent 2 → Agent 4.
- House planning: Agent 1 → Agent 3 → Agent 4.
- Land + House: Agent 1 → Agent 2 → Agent 3 → Agent 4.

Agent 2 and Agent 3 are sequential for `LAND_AND_HOUSE` because Agent 3 may require selected land price, size, location, and remaining construction budget from Agent 2.

At the foundation milestone this was a future-only plan, with no implemented agents or LangGraph orchestration. The current implementation is described above; LangGraph remains outside Agent 4 scope.

## Agent 3 Planning Output

Agent 3 supports direct `PLAN_HOUSE` planning and `LAND_AND_HOUSE` planning with selected land context from Agent 2. It creates deterministic conceptual geometry, validates hard constraints, ranks valid candidates, and writes all outputs from one canonical plan model.

Generated outputs are stored under `storage/plans/{plan_id}/`:

- `plan.json`
- floor-level SVG files
- floor-level PNG previews
- `propwise_plan.dxf`
- `summary.json`

These files are conceptual planning artifacts only. They are not approved architectural, structural, engineering, quantity-surveying, legal, planning, or construction documents.
