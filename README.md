# PropWise AI

PropWise AI is a university project for IT3041 – Information Retrieval and Web Analytics. It is planned as an agentic AI-based platform for property discovery, home planning, and construction budget estimation.

## Problem

Property search and home planning require users to connect scattered information: location preferences, property listings, land constraints, construction budgets, and final trade-offs. PropWise AI will eventually coordinate specialized agents to help users move from natural language requirements to property and planning recommendations.

## Main User Scenarios

- Find suitable properties based on user requirements.
- Plan a house concept and budget from land or construction requirements.
- Evaluate combined land and house options with remaining budget constraints.

## Four Agents

- Agent 1: Requirement & Intent Understanding.
- Agent 2: Property Search & Analysis.
- Agent 3: Home Planning & Budget Estimation.
- Agent 4: Recommendation & Decision Support.

Agent implementations are intentionally not included in this foundation phase.

## Planned Technology Stack

- Frontend: Next.js with TypeScript.
- Backend: Python with FastAPI.
- Agent orchestration: LangGraph.
- Database: Supabase PostgreSQL.
- Vector search: Supabase pgvector.
- Authentication and authorization: Supabase Auth and Row Level Security.
- CAD: Python with ezdxf.
- LLMs: OpenAI or Gemini through a provider abstraction.

Only the minimal backend scaffold dependencies are included for now.

## Repository Structure

```text
backend/    FastAPI backend scaffold, future agents, scripts, and tests
frontend/   Placeholder for the future Next.js application
data/       Raw, processed, local, sample, and knowledge dataset folders
storage/    Local/generated storage placeholder
docs/       Architecture, contracts, dataset, and team documents
```

## Dataset Folders

- `data/raw/`: local-only raw source dataset, `properties.csv`, approximately 203,874 rows.
- `data/processed/`: local-only cleaned dataset, `properties_cleaned.csv`, approximately 202,309 rows.
- `data/sample/`: Git-trackable 500-row sample generated from the cleaned dataset.
- `data/local/`: ignored local development sample, usually `properties_dev.csv`.
- `data/knowledge/`: Git-trackable placeholder for future Agent 3 knowledge files.

Full datasets and local development samples stay out of Git. The Git sample is only for tests, examples, and demonstrations.

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
