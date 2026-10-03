# PropWise AI Frontend

This is the vanilla HTML/CSS/JavaScript demo frontend. It parses requirements,
collects follow-up input, and displays final Agent 4 recommendations or owned-land
assessments, including conceptual planning details and optional grounded explanations.
Next.js was part of the original foundation plan; it is not the current frontend.

## Run Locally

Start the backend first:

```powershell
cd backend
uvicorn app.main:app --reload
```

Then start the frontend:

```powershell
cd frontend
py -m http.server 3000
```

Open:

```text
http://localhost:3000
```

The main workflow parses requirements, then submits confirmed user input to the recommendation endpoint:

```text
http://127.0.0.1:8000/api/v1/requirements/parse
http://127.0.0.1:8000/api/v1/recommendation
```

Retrieval, planning, ranking and provider calls occur server-side. The browser
requests `top_k: 10`; the LLM explanation subset is independently bounded to
5 recommendations + 2 alternatives, without removing deterministic results.
The explanation checkbox is unchecked by default. Leave it unchecked for a
provider-free demo; enabled explanations use configured backend credentials and
fall back safely on provider or validation failure. No API keys belong in the UI.

Scores are decision-support indices, not probabilities. Enum values are humanized
for display; unmet constraints, uncertainty and coverage limitations remain visible.
See the [demo checklist and acceptance results](../docs/agent4-phase3.md).
