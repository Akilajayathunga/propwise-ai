# Architecture

PropWise AI is planned as an agentic property discovery, home planning, and construction budget estimation platform.

Future request flow:

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

## Planned Components

- Frontend: Next.js with TypeScript.
- Backend: Python with FastAPI.
- Agent orchestration: LangGraph.
- Database: Supabase PostgreSQL.
- Vector search: Supabase pgvector.
- Authentication: Supabase Auth.
- Authorization: Supabase Row Level Security.
- CAD generation: Python with ezdxf.
- LLM access: OpenAI or Gemini through a provider abstraction.

## Conditional Agent Routes

- Property search: Agent 1 → Agent 2 → Agent 4.
- House planning: Agent 1 → Agent 3 → Agent 4.
- Land + House: Agent 1 → Agent 2 → Agent 3 → Agent 4.

Agent 2 and Agent 3 are sequential for `LAND_AND_HOUSE` because Agent 3 may require selected land price, size, location, and remaining construction budget from Agent 2.

This document describes future architecture only. LangGraph orchestration and agent logic are not implemented in the foundation phase.

