# Autonomous Research AI Agent

An AI research backend that accepts a user query, creates a research plan, runs tools, evaluates evidence, and returns a structured answer with sources.

## MVP Architecture

```text
User Query
   -> Planner
   -> Task List
   -> Executor
   -> Tools: search, scrape
   -> Memory
   -> Evaluator
   -> Final Report
```

## Tech Stack

- Python
- FastAPI
- Pydantic
- OpenAI-compatible LLM API
- Tavily-ready search tool interface
- Pytest

## Project Structure

```text
backend/
  app/
    agents/
      planner.py
      executor.py
      evaluator.py
      synthesizer.py
    core/
      config.py
    memory/
      research_memory.py
    schemas/
      research.py
    services/
      llm.py
    tools/
      search_web.py
      scrape_page.py
    main.py
  tests/
```

## Setup

Install Python 3.11+ first, then run:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

## Root Development Workflow

You can now start the full app from the repository root:

```bash
npm install
npm run dev
```

This will start:

- Backend API on `http://127.0.0.1:8000`
- Frontend on `http://localhost:5173`

Frontend API base URL defaults to the backend URL above. If needed, set `frontend/.env`:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

## API

### `POST /research`

Request:

```json
{
  "query": "Research the impact of AI in healthcare in 2025",
  "max_tasks": 4
}
```

Response:

```json
{
  "query": "...",
  "plan": [...],
  "steps": [...],
  "sources": [...],
  "answer": "...",
  "evaluation": {
    "is_supported": true,
    "confidence": "medium",
    "missing_evidence": []
  }
}
```

## First Milestone

The current goal is a working backend MVP:

- receive query
- generate research tasks
- execute search/scrape-ready tool calls
- clean raw tool output
- assign numbered citations and reliability labels
- synthesize final answer with citations
- evaluate whether the answer is supported

## Future Improvements

- React dashboard
- streaming task progress
- vector memory
- source reliability ranking
- PDF export
- cost and latency tracking
- multi-agent reviewer workflow
# research-console
