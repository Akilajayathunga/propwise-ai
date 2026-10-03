# PropWise AI Frontend

This is the static HTML/CSS/JavaScript application for property search and
conceptual home planning. It presents listings, budget context, floor plans,
and downloads without exposing the internal intent or raw JSON response.

## Run Locally

Start the backend:

```powershell
cd backend
uvicorn app.main:app --reload
```

Start the frontend in another terminal:

```powershell
cd frontend
py -m http.server 3000
```

Open <http://127.0.0.1:3000/>. Local frontend requests use
`http://127.0.0.1:8000` by default; no LLM key is needed for the deterministic
workflow.

## Deployment

For a same-origin reverse proxy, leave the `propwise-api-base` meta tag in
`index.html` empty and route `/api` and `/plans` to the backend. If the backend
has a separate origin, set that meta tag to its public HTTPS base URL and allow
the frontend origin in the backend CORS configuration. Do not put API keys in
the frontend. Conceptual plans and cost estimates require professional review.
