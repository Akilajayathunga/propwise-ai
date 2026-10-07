# PropWise AI

PropWise AI is a university project for IT3041 – Information Retrieval and Web Analytics. It implements property discovery, conceptual home planning, construction budget estimation, and final recommendation and decision support.

## Problem

Property search and home planning require users to connect scattered information: location preferences, property listings, land constraints, construction budgets, and final trade-offs. PropWise AI coordinates specialized agents through direct backend calls to move from natural-language requirements to property and planning recommendations.

## Main User Scenarios

- Find suitable properties based on user requirements.
- Plan a house concept and budget from land or construction requirements.
- Evaluate combined land and house options with remaining budget constraints.

## Project Idea and User Journey

PropWise AI is a decision-support application, not an automated estate agent or
architect. A user describes what they want in ordinary language, reviews any
missing details, and receives property evidence, a conceptual home plan, or both.
The system then explains the trade-offs behind its recommendations rather than
presenting a single unexplained answer.

For example, someone looking for land near Kottawa and a two-bedroom house can
state a total project budget. PropWise AI identifies the requirements, searches
available listings, estimates what could be built on suitable land, and compares
the resulting options against the original budget. A user who already owns land
can go straight to conceptual planning without a property search.

The implemented request paths are:

| User goal | Workflow | Result |
| --- | --- | --- |
| Find or compare property | Agent 1 -> Agent 2 -> Agent 4 | Relevant listings, comparisons, and recommendations |
| Plan on owned land | Agent 1 -> Agent 3 -> Agent 4 | Conceptual plan, budget context, and owned-land assessment |
| Buy land and build a house | Agent 1 -> Agent 2 -> Agent 3 -> Agent 4 | Land-and-house options assessed against the total budget |

## Four Agents

These agents are specialized backend components connected by direct Python calls.
They do not represent four independent chatbots or a LangGraph workflow in the
current demo.

### Agent 1: Requirement and Intent Understanding

Agent 1 converts a natural-language request into structured requirements. It
classifies the user's goal, extracts details such as location, transaction type,
budget, land size, and rooms, then validates the result. The application can ask
follow-up questions when information needed for a workflow is missing. The
current parsing path is deterministic and does not make a live LLM call.

**Concepts used:** rule-based intent classification, information extraction,
structured schemas, validation, and clarification.

### Agent 2: Property Search and Analysis

Agent 2 searches the available property dataset using the structured request.
It applies hard filters first, then scores and ranks matching listings by
relevance. If the strict search is empty, it can retry with relaxed budget and
bedroom constraints, explicitly warning that it did so. It also returns summary
analysis of the matched properties. Listings are dataset records, not a
guarantee of live availability or verified suitability.

**Concepts used:** information retrieval, constraint filtering, relevance
scoring, ranking, fallback search, and descriptive analysis.

### Agent 3: Home Planning and Budget Estimation

Agent 3 uses owned-land details or selected land evidence together with the
requested rooms and budget. It analyses site dimensions, builds a room program,
generates candidate layouts, checks constraints, and selects a scored conceptual
plan. It estimates construction costs from configured assumptions and can
produce plan JSON, SVG and PNG previews, a DXF drawing, and downloadable plan
files. The output includes warnings where site fit or cost assumptions need
verification.

**Concepts used:** spatial constraints, room zoning and adjacency, candidate
generation, layout optimization, budget estimation, and plan rendering.
Generated plans and costs are preliminary, not approved construction documents
or contractor quotations.

### Agent 4: Recommendation and Decision Support

Agent 4 combines the original requirements with server-obtained property and/or
planning evidence. Its deterministic engine checks hard-constraint eligibility,
assesses budget and planning evidence, ranks suitable options, and provides
alternatives, comparisons, warnings, and coverage information. For owned land,
it assesses the plan without inventing a property ranking. An optional LLM can
write a grounded explanation, but it cannot change eligibility, scores, order,
or the final decision; a deterministic explanation remains available as a
fallback.

**Concepts used:** multi-criteria decision support, eligibility checks,
evidence-based ranking, explainability, provenance, and guarded LLM synthesis.

Agent 4 is implemented and accepted as **READY FOR FINAL DEMO**.

The accepted explanation configuration uses Gemini `gemini-3.1-flash-lite` and
`propwise-agent4-explanation-v5`. Credentials remain in local configuration and must
never be committed. OpenAI remains supported by the provider adapter.

See [current architecture](docs/architecture.md), [grounded explanations](docs/agent4-phase2.md)
and [API, demo and final acceptance results](docs/agent4-phase3.md).
The final acceptance snapshot records **305 Agent 4 tests** and **398 full backend
tests passing**, with no failures. These are overlapping suites, not additive totals.

## Current Demo Stack

The demo uses vanilla HTML/CSS/JavaScript, Python/FastAPI, existing property retrieval
and conceptual planning services, and direct Agent 4 orchestration. LangGraph,
Next.js, Supabase migration and pgvector are not required by the implemented Agent 4 flow.
See the [frontend instructions](frontend/README.md) to run the browser interface.

## Historical Foundation Technology Plan

The original proposed stack below is retained as a design record, not a description
of the deployed demo:

- Frontend: Next.js with TypeScript.
- Backend: Python with FastAPI.
- Agent orchestration: LangGraph.
- Database: Supabase PostgreSQL.
- Vector search: Supabase pgvector.
- Authentication and authorization: Supabase Auth and Row Level Security.
- CAD: Python with ezdxf.
- LLMs: OpenAI or Gemini through a provider abstraction.

The foundation originally included only scaffold dependencies; current dependencies are listed in `backend/requirements.txt`.

## Repository Structure

```text
backend/    FastAPI routes, agent implementations, scripts, and tests
frontend/   Vanilla HTML/CSS/JavaScript demo with Agent 4 results
data/       Raw, processed, local, sample, and knowledge dataset folders
storage/    Generated conceptual planning artifacts
docs/       Architecture, contracts, dataset, and team documents
```

## Dataset Folders

- `data/raw/`: raw source dataset, `properties.csv`, approximately 203,874 rows.
- `data/processed/`: cleaned dataset, `properties_cleaned.csv`, approximately 202,309 rows.
- `data/sample/`: Git-trackable 500-row sample generated from the cleaned dataset.
- `data/local/`: development sample, usually `properties_dev.csv`.
- `data/knowledge/`: Git-trackable placeholder for future Agent 3 knowledge files.

Large CSV datasets should be committed through Git LFS. The Git sample is still useful for tests, examples, and demonstrations.

## Backend Setup

Create and activate a Python virtual environment from the repository root:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install backend dependencies:

```powershell
pip install -r backend\requirements.txt
```

Run FastAPI:

```powershell
cd backend
uvicorn app.main:app --reload
```

Open the API docs:

```text
http://127.0.0.1:8000/docs
```

Health check:

```text
http://127.0.0.1:8000/api/v1/health
```

## Sample Dataset Generation

Place the cleaned dataset at `data/processed/properties_cleaned.csv`, or copy `backend/.env.example` to `backend/.env` locally and set `CLEANED_DATASET_PATH`. Do not commit `.env`.

Create the Git sample:

```powershell
cd backend
python -m scripts.create_sample_dataset --mode git
```

Create the local development sample:

```powershell
cd backend
python -m scripts.create_sample_dataset --mode development --size 10000
```

The samples must originate from the real cleaned dataset. They are not substitutes for the final full cleaned dataset of approximately 202,309 records.

## Git Workflow

Each member should work on a feature branch:

- `feature/agent1-requirements`
- `feature/agent2-property-search`
- `feature/agent3-home-planning`
- `feature/agent4-recommendation`

## Dataset Note

The raw dataset of approximately 203,874 rows and the cleaned dataset of approximately 202,309 rows must not be committed to GitHub. Use environment variables for local dataset paths and commit only safe samples such as `data/sample/properties_sample.csv`.
