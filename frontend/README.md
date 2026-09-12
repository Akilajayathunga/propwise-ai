# PropWise AI Frontend

This is a dependency-free testing frontend for Agent 1. It can be replaced later when the full Next.js + TypeScript application is built.

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

The UI posts requests to:

```text
http://127.0.0.1:8000/api/v1/requirements/parse
```
