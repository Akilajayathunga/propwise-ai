# PropWise AI

PropWise AI is a university project for IT3041 – Information Retrieval and Web Analytics. It implements property discovery, conceptual home planning, construction budget estimation, and final recommendation and decision support.

## Problem

Property search and home planning require users to connect scattered information: location preferences, property listings, land constraints, construction budgets, and final trade-offs. PropWise AI coordinates specialized agents through direct backend calls to move from natural-language requirements to property and planning recommendations.

## Main User Scenarios

- Find suitable properties based on user requirements.
- Plan a house concept and budget from land or construction requirements.
- Evaluate combined land and house options with remaining budget constraints.

## Four Agents

- Agent 1: Requirement & Intent Understanding.
- Agent 2: Property Search & Analysis.
- Agent 3: Home Planning & Budget Estimation.
- Agent 4: Recommendation & Decision Support.

Agent 4 is implemented and accepted as **READY FOR FINAL DEMO**. Its deterministic
Python engine owns eligibility, budget assessment, final scores/ranking, alternatives,
comparisons, candidate coverage and owned-land assessment. Optional Gemini output
only explains that decision; it cannot change it.

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
