# Research Console — Project Specification

> **Status:** Living document · Generated 2026-06-28 · Reflects the current `main` branch.
> This spec documents the system **as it is built today**. Update sections as the project evolves.

---

## 1. Overview

**Research Console** (a.k.a. *Autonomous Research AI Agent*) is a full-stack application that turns a single research question into a cited, evaluated answer. It runs an autonomous, multi-step pipeline — **plan → search/scrape → clean → synthesize → evaluate** — and exposes the entire run (tasks, pipeline steps, sources, answer, support evaluation) through a React dashboard.

A core design principle is **honest state reporting**: the console never fakes a result. Tool failures, LLM failures, and low-confidence evaluations are surfaced explicitly rather than hidden.

### Project layout (monorepo)

```
Research-Console/
├── backend/        # FastAPI service (Python) — the agent pipeline + API
├── frontend/       # React + Vite SPA (TypeScript) — the dashboard
├── package.json    # Root dev scripts (runs backend + frontend together)
├── README.md
└── spec.md         # ← this file
```

---

## 2. Tech Stack

### Backend
| Concern | Choice | Version |
|---|---|---|
| Language | Python | 3.12 (3.11+ supported) |
| Web framework | FastAPI | 0.115.6 |
| ASGI server | Uvicorn (standard) | 0.34.0 |
| Validation / schemas | Pydantic | 2.11.7 |
| Settings | pydantic-settings | 2.11.0 |
| HTTP client | httpx (async) | 0.28.1 |
| HTML parsing | beautifulsoup4 | 4.12.3 |
| ORM | SQLAlchemy | 2.0.39 |
| Env loading | python-dotenv | 1.0.1 |
| Tests | pytest + pytest-asyncio | 8.3.4 / 0.25.0 |

### Frontend
| Concern | Choice | Version |
|---|---|---|
| Language | TypeScript | ~6.0.2 |
| UI library | React | 19.2.5 |
| Build tool | Vite | 8.0.x |
| State / data fetching | Redux Toolkit + RTK Query | 2.12.0 |
| React bindings | react-redux | 9.3.0 |
| Styling | Hand-written CSS (design tokens via CSS variables) | — |
| Fonts | Geist, JetBrains Mono (Google Fonts) | — |
| Linting | ESLint + typescript-eslint | 10.x / 8.x |

### External services
| Service | Purpose | Required? |
|---|---|---|
| **LLM API** (OpenAI-compatible **or** Google Gemini) | Planning, synthesis, evaluation | Yes (`OPENAI_API_KEY`) |
| **Tavily** | Live web search | Optional (falls back to a "not configured" notice) |

> **LLM dual-mode:** [`llm.py`](backend/app/services/llm.py) auto-detects Gemini when `OPENAI_BASE_URL` contains `generativelanguage.googleapis.com` and uses the Gemini `generateContent` shape; otherwise it uses the OpenAI `chat/completions` shape. The repo is currently configured for **Gemini 2.5 Flash**.

---

## 3. Architecture

### 3.1 High-level data flow

```
                          ┌───────────────────────────────────────────────┐
   POST /research         │                  FastAPI app                   │
  { query, max_tasks } ──▶│                                                │
                          │   Planner ─▶ Executor ─▶ Cleanup ─▶ Synthesizer│─▶ Evaluator
                          │     │           │           │           │        │     │
                          │     │           ▼           ▼           ▼        │     ▼
                          │     │     Tools(search,   dedupe +   cited      │  support +
                          │     │      scrape)        classify   answer     │  confidence
                          │     ▼                                           │
                          │  task list                                      │
                          └───────────────────────┬───────────────────────┘
                                                   │  persist full run (SQLite)
                                                   ▼
                                          GET /research (history)
                                          GET /research/{id} (full run)
                                                   │
                                                   ▼
                                       React dashboard (RTK Query)
```

### 3.2 Pipeline stages (the five `ExecutionStep`s)

The orchestration lives in [`main.py`](backend/app/main.py) inside the `POST /research` handler. It is **linear and sequential** and produces a named `ExecutionStep` per stage, each marked `completed` or `failed`:

1. **planning** — `ResearchPlanner.create_plan()` decomposes the query into tool-ready tasks. On LLM failure → `fallback_plan()` (heuristic 2-task plan) and the step is marked `failed`.
2. **tool_execution** — `ResearchExecutor.execute()` runs each task's tool. Individual tool failures are caught and recorded; the step is `failed` if any tool errored.
3. **cleanup** — `ResearchCleanupService.clean_observations()` normalizes text, dedupes sources by URL, classifies each source (type + reliability), and assigns numbered citations.
4. **synthesis** — `ResearchSynthesizer.create_answer()` writes a cited answer from the cleaned evidence. On LLM failure → a transparent placeholder answer + `failed` step.
5. **evaluation** — `ResearchEvaluator.evaluate()` checks whether the answer is supported by the evidence and returns confidence + missing evidence. On LLM failure → `fallback_evaluation()`.

Each stage is **failure-isolated**: one failure degrades that stage but never aborts the run, so the user always gets a partial, honestly-labeled result.

### 3.3 Resilience / fallback behavior
- **No LLM key** → `LLMError` raised with a clear message.
- **No Tavily key** → search tool returns a "not configured" source instead of crashing.
- **Tool exception** (timeout, 4xx/5xx, bad URL) → captured into the `Observation.metadata.error`, run continues.
- **Invalid LLM JSON** → `LLMError` with the first 200 chars of the bad output for debugging.

---

## 4. Agents

All "agents" are thin classes wrapping prompt + parse logic over a shared `LLMClient`. They live in [`backend/app/agents/`](backend/app/agents/).

| Agent | File | Responsibility | Fallback |
|---|---|---|---|
| **Planner** | `planner.py` | Decompose the query into ≤ `max_tasks` tool-ready `ResearchTask`s (strict JSON). Honors the cap even if the model ignores it. | `fallback_plan()` — heuristic background + risks/limitations tasks |
| **Executor** | `executor.py` | Dispatch each task to its named tool; record observations; isolate tool failures. | Per-task error capture (unknown tool / exception) |
| **Synthesizer** | `synthesizer.py` | Write a structured, cited answer (`Summary`, `Key impacts`, `Risks and limitations`, `Sources used`) using **only** provided evidence + numbered citation context. | Transparent placeholder answer on LLM failure |
| **Evaluator** | `evaluator.py` | Return strict JSON: `is_supported`, `confidence`, `missing_evidence[]`, `notes`. | `fallback_evaluation()` — infers support from evidence presence |

> **Note:** This is a hand-rolled sequential multi-agent setup (no LangChain/LangGraph/CrewAI). There is currently **no** dedicated Analysis, Citation, or Reviewer agent.

---

## 5. Tools

Tools live in [`backend/app/tools/`](backend/app/tools/) and are registered in a dict in `main.py`. Each implements `async def run(self, task: ResearchTask) -> Observation`.

| Tool | File | Behavior |
|---|---|---|
| **search_web** | `search_web.py` | Calls **Tavily** `/search` (`search_depth: basic`, `max_results: 5`). Maps results → `Source[]`. Returns a "not configured" source if `TAVILY_API_KEY` is missing. |
| **scrape_page** | `scrape_page.py` | `GET`s a URL (follows redirects), parses with BeautifulSoup, extracts `<p>` text (capped at 3000 chars) and `<title>`. |

The planner may only emit these two tool names (enforced by the `ResearchTask.tool` `Literal`).

---

## 6. Services

| Service | File | Responsibility |
|---|---|---|
| **LLMClient** | `services/llm.py` | Unified async LLM client. `complete_text()` and `complete_json()` (strips code fences, parses JSON). Dual OpenAI-compatible / Gemini support. Rich `LLMError` messages (HTTP status + body excerpt). `temperature=0.2`, 45s timeout. |
| **ResearchCleanupService** | `services/research_cleanup.py` | Text normalization (strips markdown/URLs/cookie noise), URL-based dedup, citation numbering, and **domain-heuristic source classification** → `(source_type, reliability)`. Builds the numbered `citation_context` string for the synthesizer. |
| **ResearchMemory** | `memory/research_memory.py` | In-memory, **per-request** store of observations + unique sources. Not persisted across runs. |

### Source classification (heuristic)
`classify_source()` maps a domain to `(type, reliability)` via allowlists:
- `.gov` / known gov domains (nih, who, cdc, fda, europa…) → `government / high`
- `.edu` / known academic (nature, sciencedirect, arxiv, ieee, acm…) → `academic / high`
- Known orgs (worldbank, oecd, un, imf…) → `organization / high`; other `.org` → `organization / medium`
- Known consultancies (mckinsey, gartner…) → `industry / medium`
- Major news (reuters, bbc, nyt…) → `news / medium`; blog/substack/magazine → `news / low`
- Other `.com` → `news / medium`; everything else → `unknown / unknown`

---

## 7. Data Models

### 7.1 Pydantic schemas ([`schemas/research.py`](backend/app/schemas/research.py))

| Schema | Key fields |
|---|---|
| `ResearchRequest` | `query` (min 3 chars), `max_tasks` (1–8, default 4) |
| `ResearchTask` | `id`, `description`, `tool` (`search_web`\|`scrape_page`), `input`, `priority` |
| `ResearchPlan` | `tasks: ResearchTask[]` |
| `Source` | `citation_id?`, `title`, `url`, `snippet`, `reliability` (unknown\|low\|medium\|high), `source_type` |
| `Observation` | `task_id`, `task`, `tool`, `result`, `sources[]`, `metadata{}` |
| `Evaluation` | `is_supported`, `confidence`, `missing_evidence[]`, `notes` |
| `ExecutionStep` | `name`, `status` (completed\|failed), `detail` |
| `ResearchResponse` | `research_id?`, `query`, `plan[]`, `steps[]`, `sources[]`, `observations[]`, `answer`, `evaluation` |
| `ResearchRunSummary` | `research_id`, `query`, `created_at` |
| `ResearchRunListResponse` | `items: ResearchRunSummary[]` |

### 7.2 Database ([`models/research_run.py`](backend/app/models/research_run.py))

**Engine:** SQLAlchemy 2.0 + SQLite (`sqlite:///./research.db` by default; swappable via `DATABASE_URL`). Tables auto-created on startup via `Base.metadata.create_all` in the FastAPI `lifespan`.

**Table `research_runs`:**
| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | indexed |
| `query` | String(1000) | |
| `plan`, `steps`, `sources`, `observations` | JSON | full run snapshot |
| `answer` | String | |
| `evaluation` | JSON | |
| `created_at` | DateTime(tz) | UTC, indexed |

> The TS types in [`frontend/src/features/research/types.ts`](frontend/src/features/research/types.ts) mirror these schemas 1:1.

---

## 8. API

Base URL (dev): `http://127.0.0.1:8000`. CORS origins from `CORS_ALLOW_ORIGINS` (defaults to localhost/127.0.0.1 ports 5173–5175).

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | `{ "status": "ok" }` |
| `POST` | `/research` | Run the full pipeline for `{ query, max_tasks }`; persists and returns the complete `ResearchResponse`. |
| `GET` | `/research?limit=N` | List recent run summaries (limit clamped 1–100, default 20), newest first. |
| `GET` | `/research/{id}` | Fetch one full run; `404` if not found. |

### Example — `POST /research`
```json
// request
{ "query": "What is the scientific consensus on direct air capture at scale?", "max_tasks": 6 }

// response (abridged)
{
  "research_id": 12,
  "query": "...",
  "plan": [{ "id": 1, "description": "...", "tool": "search_web", "input": "...", "priority": "high" }],
  "steps": [{ "name": "planning", "status": "completed", "detail": "Created 6 research tasks." }],
  "sources": [{ "citation_id": 1, "title": "...", "url": "...", "reliability": "high", "source_type": "academic" }],
  "observations": [ ... ],
  "answer": "## Where the consensus stands\n...[1][3]...",
  "evaluation": { "is_supported": true, "confidence": "medium", "missing_evidence": ["..."], "notes": "..." }
}
```

Interactive docs available at `http://127.0.0.1:8000/docs` (FastAPI auto-generated Swagger UI).

---

## 9. Folder Structure

```
Research-Console/
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── planner.py          # query → task list
│   │   │   ├── executor.py         # tasks → observations
│   │   │   ├── synthesizer.py      # evidence → cited answer
│   │   │   └── evaluator.py        # answer → support evaluation
│   │   ├── tools/
│   │   │   ├── search_web.py       # Tavily web search
│   │   │   └── scrape_page.py      # URL → readable text
│   │   ├── services/
│   │   │   ├── llm.py              # OpenAI/Gemini client
│   │   │   └── research_cleanup.py # dedupe, classify, cite
│   │   ├── memory/
│   │   │   └── research_memory.py  # per-run in-memory store
│   │   ├── schemas/
│   │   │   └── research.py         # Pydantic models
│   │   ├── models/
│   │   │   └── research_run.py     # SQLAlchemy ORM model
│   │   ├── core/
│   │   │   ├── config.py           # settings (env-driven)
│   │   │   └── database.py         # engine + session
│   │   └── main.py                 # FastAPI app + pipeline orchestration
│   ├── requirements.txt
│   ├── .env / .env.example
│   └── (.venv/, research.db — gitignored)
│
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── store.ts            # Redux store
│   │   │   └── hooks.ts            # typed useAppDispatch/Selector
│   │   ├── features/research/
│   │   │   ├── researchApi.ts      # RTK Query endpoints
│   │   │   ├── researchSlice.ts    # UI state (selectedRunId, sidebarOpen)
│   │   │   └── types.ts            # TS mirrors of backend schemas
│   │   ├── components/
│   │   │   ├── layout/             # Header, Sidebar, Footer
│   │   │   └── research/           # ResearchForm, HistoryList, RunOverview,
│   │   │                           #   Timeline, SourcesGrid, AnswerCard,
│   │   │                           #   EmptyState, ErrorBanner, ResearchWorkspace
│   │   ├── utils/format.ts         # hostname, answer blocks, labels
│   │   ├── App.tsx / App.css       # shell + "Instrument" design styles
│   │   ├── index.css               # theme tokens + fonts
│   │   └── main.tsx                # React entry (Provider + StrictMode)
│   ├── vite.config.ts              # port pinned to 5173 (strictPort)
│   └── package.json
│
├── package.json                    # root dev orchestration
├── README.md
└── spec.md
```

---

## 10. Frontend Architecture

- **Entry:** `main.tsx` mounts `<App>` inside a Redux `<Provider>` and `<StrictMode>`.
- **Shell:** `App.tsx` → `app-shell` containing `Header`, a `content-grid` (`Sidebar` + `ResearchWorkspace`), and `Footer`.
- **State:**
  - **Server state** via **RTK Query** ([`researchApi.ts`](frontend/src/features/research/researchApi.ts)): `getHistory`, `getRun`, `createResearch` with tag-based cache invalidation (`History`, `Run`).
  - **UI state** via a small slice ([`researchSlice.ts`](frontend/src/features/research/researchSlice.ts)): `selectedRunId`, `sidebarOpen`.
- **Data fetching flow:** `HistoryList` loads recent runs and auto-selects the newest; selecting a run sets `selectedRunId`; `ResearchWorkspace` fetches that run via `useGetRunQuery` and renders the stages.
- **API base URL:** `VITE_API_BASE_URL` (defaults to `http://127.0.0.1:8000`).

### Component map
| Component | Role |
|---|---|
| `Header` | Eyebrow + title + subtitle + mobile menu toggle |
| `Sidebar` | Drawer wrapper for `ResearchForm` + `HistoryList` (slide-in on mobile) |
| `ResearchForm` | New-run form (question + max tasks) → `createResearch` |
| `HistoryList` | Recent runs, refresh, active selection |
| `ResearchWorkspace` | Orchestrates the result view; handles empty/loading/error states |
| `RunOverview` | Run id, query, 3 metric cards (Tasks / Steps / Sources) |
| `Timeline` | Vertical numbered **pipeline** with status dots/pills |
| `AnswerCard` | Synthesized answer (heading/paragraph blocks) + evaluation box |
| `SourcesGrid` | Source cards (citation, reliability pill, host, snippet) |
| `EmptyState` / `ErrorBanner` | Honest empty + failure surfaces |

---

## 11. Design System — "Instrument"

Imported from a Claude Design study and implemented as the live theme. Dark, instrument-panel aesthetic with an amber/gold accent.

| Token | Value |
|---|---|
| Page / Shell / Panel | `#0b0c0d` / `#131517` / `#181a1d` |
| Accent | `#e8a13c` (amber) on `#0b0c0d` text |
| OK / Fail / Medium | `#5ec98a` / `#e8593f` / `#e8a13c` |
| Text strong / body / muted | `#f2f1ec` / `#c6c8c8` / `#7e8488` |
| Fonts | Geist (sans/head), JetBrains Mono (mono) |
| Radius | 11px (cards), 16px (shell) |

**Layout:** centered shell (max 1320px); 330px sidebar + fluid main; pipeline-beside-answer grid that stacks ≤1180px; sidebar collapses to a drawer ≤980px; single-column ≤680px. Color tints use `rgba(var(--*-rgb), …)` for broad browser support.

---

## 12. Configuration

Backend settings ([`core/config.py`](backend/app/core/config.py)) are environment-driven (`backend/.env`):

| Variable | Default | Purpose |
|---|---|---|
| `APP_NAME` | "Autonomous Research AI Agent" | App title |
| `APP_ENV` | development | Environment label |
| `DATABASE_URL` | `sqlite:///./research.db` | DB connection |
| `OPENAI_API_KEY` | "" | LLM key (**required**) |
| `OPENAI_BASE_URL` | OpenAI / Gemini base | Switches LLM provider |
| `OPENAI_MODEL` | `gemini-2.5-flash` (current) | Model id |
| `TAVILY_API_KEY` | "" | Web search (optional) |
| `CORS_ALLOW_ORIGINS` | localhost/127.0.0.1 :5173–5175 | Allowed frontend origins |

Frontend: `VITE_API_BASE_URL` in `frontend/.env` (optional).

> ⚠️ **Secrets:** `backend/.env` is gitignored. Never commit real keys. Rotate any key that has been shared.

---

## 13. Setup & Run

### Prerequisites
Python 3.12 (3.11+), Node.js (for the frontend), npm.

### One-command dev (from repo root)
```bash
npm install
npm run dev          # runs backend (8000) + frontend (5173) together via concurrently
```

### Run separately
```bash
# Backend
npm run dev:backend  # py -3.12 -m uvicorn app.main:app --reload --port 8000 --app-dir backend

# Frontend
npm run dev:frontend # vite dev server on http://localhost:5173
```

### Build / test
```bash
npm run build:frontend   # tsc -b && vite build
npm run test:backend     # pytest (backend/tests)
```

### First-time backend env
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env   # then fill in OPENAI_API_KEY (+ TAVILY_API_KEY)
```

---

## 14. Screenshots

> _Placeholder — add images here. Suggested: create `docs/screenshots/` and embed._

| View | Image |
|---|---|
| Result (loaded run) | `![Result view](docs/screenshots/result.png)` |
| Running / synthesizing | `![Running](docs/screenshots/running.png)` |
| Empty state | `![Empty](docs/screenshots/empty.png)` |
| Error state | `![Error](docs/screenshots/error.png)` |
| Mobile drawer | `![Mobile](docs/screenshots/mobile.png)` |

---

## 15. Current Scope & Known Limitations

**Implemented:** core autonomous research loop (plan→execute→clean→synthesize→evaluate), Tavily web search + HTML scrape, domain-heuristic credibility, numbered citations, SQLite persistence + history, dual OpenAI/Gemini LLM support, responsive React dashboard with honest empty/error/loading states.

**Not yet implemented (notable gaps):**
- No academic source APIs (arXiv, Semantic Scholar, PubMed), GitHub, or data portals — web search only.
- No RAG / vector DB — evidence is concatenated into the prompt.
- No document intelligence (PDF/DOCX upload, OCR, tables/figures).
- No citation styles (APA/MLA/IEEE/BibTeX) or report export.
- No workspace (projects/folders/tags), auth, collaboration, or cross-run memory.
- No streaming progress (run is request/response; UI waits for completion).
- Executor runs tasks **sequentially** (no parallelism).
- No automated test coverage wired up yet (pytest configured, `backend/tests/` referenced).

---

## 16. Roadmap & Future Improvements

The following roadmap outlines the planned evolution of the Research Console from its current MVP into a production-grade autonomous AI research platform.

### 16.0 How to read this roadmap

**Status legend** (applied per phase below):
- 🟢 **Started** — partially implemented in the current codebase; needs extension.
- 🟡 **Next** — highest leverage, builds directly on what exists today.
- ⚪ **Later** — valuable but depends on earlier phases or new infrastructure.

**Recommended build order** (sequenced by leverage and dependencies, not strictly by phase number):

| Order | Work item | Phase | Why first | Depends on |
|---|---|---|---|---|
| 1 | Parallelize executor (`asyncio.gather`) + retry/backoff | 9 | Cheap, immediate latency win; executor is sequential today | — |
| 2 | Academic search tools (arXiv, Semantic Scholar — free, no key) | 1 | Biggest research-quality jump; plugs into the existing tool registry | — |
| 3 | Citation Agent + export (APA/MLA/IEEE/BibTeX) | 2 | High perceived value, cheap; `Source` objects already structured | — |
| 4 | RAG pipeline + vector DB (Chroma) | 3 | Unlocks document chat, analysis, scale; foundational | tools (1–2) |
| 5 | Streaming progress (SSE/WebSocket) | 9 | Replaces request/response wait with live pipeline | — |
| 6 | Document intelligence (PDF via PyMuPDF) | 4 | Core "researcher" use case | RAG (4) |
| 7 | Analysis + Reviewer agents | 2 | Contradiction/gap detection, QA pass | RAG (4) |
| 8 | Auth + workspace + AI memory | 5, 8, 10 | Turns the tool into a platform | — |

> **Grounding note:** The agent already implements a hand-rolled sequential version of Phases 1–2 (Planner, Search/Executor, Synthesizer/Writer, Evaluator/Verifier). The roadmap **extends** these into specialized, parallel, RAG-backed agents — it does not start from zero. See §4 and §15 for the current baseline.

### Phase 1 — Research Intelligence  🟡 Next

> Search today is **Tavily web-only**. This phase adds academic + specialized sources via new tools in the existing `tools/` registry (each implements `async run(task) -> Observation`). arXiv and Semantic Scholar are free and key-less — start there.

#### Advanced Search Integrations

* Google Scholar integration
* arXiv API integration
* Semantic Scholar API
* PubMed support
* IEEE Xplore support
* ACM Digital Library support
* CrossRef metadata lookup
* ResearchGate metadata retrieval

#### Additional Search Sources

* GitHub repository search
* Stack Overflow search
* Reddit discussions
* LinkedIn public articles
* Technical blogs
* Government datasets
* Kaggle datasets
* Open Data portals

#### Search Improvements

* Semantic search
* Query expansion
* Search refinement
* Duplicate source removal
* Intelligent ranking
* Domain filtering
* Date filtering
* Multi-language search

---

### Phase 2 — Multi-Agent Architecture  🟢 Started

Introduce specialized autonomous agents. **Four of these already exist in a basic form** (see §4) — this phase upgrades them (parallel, RAG-backed) and adds the three missing agents (Analysis, Citation, Reviewer). A later step replaces the hand-rolled sequential orchestration with a graph runner (LangGraph) to enable retries, branching, and self-reflection.

> **Status key:** `[exists]` = present today and to be extended · `[new]` = not yet built.

#### Planner Agent  `[exists — planner.py]`

* Understand research objectives
* Decompose complex problems
* Prioritize research tasks

#### Search Agent  `[exists — executor.py + tools/]`

* Perform parallel searches *(currently sequential — see Phase 9)*
* Retrieve academic papers *(needs Phase 1 tools)*
* Discover trusted sources

#### Analysis Agent  `[new]`

* Compare research papers
* Detect contradictions
* Identify trends
* Discover research gaps

#### Verification Agent  `[exists — evaluator.py]`

* Cross-check facts
* Verify statistics
* Detect misinformation
* Confidence scoring

#### Citation Agent  `[new]`

* Generate APA citations
* MLA
* IEEE
* Harvard
* Chicago
* BibTeX

#### Writer Agent  `[exists — synthesizer.py, single-format]`

Generate (currently one structured answer; expand to multiple document types):

* Executive Summary
* Literature Review
* Technical Report
* Whitepaper
* Research Paper
* Business Report

#### Reviewer Agent  `[new]`

* Grammar checking
* Citation validation
* Logical consistency
* Hallucination detection
* Completeness verification

---

### Phase 3 — Retrieval-Augmented Generation (RAG)  🟡 Next

> **Foundational.** Today evidence is concatenated straight into the synthesis prompt (no retrieval, no embeddings). RAG is the prerequisite for document chat (Phase 4), deeper analysis (Phase 2), and scaling past a handful of sources. Recommended first DB: **Chroma** (local, zero-ops).

Implement a complete RAG pipeline.

Features include:

* Document chunking
* Embedding generation
* Vector database
* Semantic retrieval
* Hybrid retrieval
* Metadata filtering
* Citation-aware retrieval
* Incremental indexing

Supported vector databases:

* Chroma
* Qdrant
* Pinecone
* Weaviate

---

### Phase 4 — Document Intelligence  ⚪ Later

> Depends on Phase 3 (RAG) for chunking/indexing uploaded files. Start with **PDF (PyMuPDF)** — the most common research format — before DOCX/PPTX.

Support uploaded documents.

Supported formats:

* PDF
* DOCX
* PPTX
* HTML
* Markdown
* TXT

Capabilities:

* OCR
* Table extraction
* Figure extraction
* Formula recognition
* Citation extraction
* Section indexing
* Interactive document chat

---

### Phase 5 — Research Workspace  ⚪ Later

> Needs a user/auth model (Phase 10) to scope projects per user. Today all runs share one global history stream.

Provide a complete research management environment.

Features:

* Projects
* Folders
* Tags
* Saved searches
* Notes
* Highlights
* Collections
* Bookmarks
* Version history

---

### Phase 6 — Collaboration  ⚪ Later

> Depends on Phase 5 (workspace) and Phase 10 (auth/multi-tenancy).

Team research capabilities.

Features:

* Shared workspaces
* Role-based permissions
* Comments
* Live collaboration
* Research sharing
* Activity logs
* Team dashboards

---

### Phase 7 — Analytics & Visualization  ⚪ Later

> Knowledge graphs and citation networks become feasible once academic metadata (Phase 1: Semantic Scholar / CrossRef) and RAG indexing (Phase 3) are in place.

Interactive visualizations including:

* Citation networks
* Knowledge graphs
* Timeline visualization
* Topic clusters
* Publication trends
* Research heatmaps
* Institution rankings
* Country-wise analytics

---

### Phase 8 — AI Memory  ⚪ Later

> `ResearchMemory` exists but is **per-request only**. This phase persists memory across runs (and per user, once Phase 10 lands).

Persistent memory system.

Store:

* User preferences
* Previous research
* Citation preferences
* Frequently used sources
* Writing style
* Research history

---

### Phase 9 — Performance Improvements  🟡 Next (partly quick wins)

> The two cheapest, highest-impact items in the whole roadmap live here: **parallel executor** (`asyncio.gather` in `executor.py`) and **streaming progress**. Pull these forward — see the build-order table in §16.0.

Backend

* Async task execution
* Parallel agent execution *(executor is sequential today)*
* Smart caching
* Retry mechanisms
* Rate limiting
* Background workers
* Queue processing

Frontend

* Streaming responses *(run is request/response today; UI waits)*
* Real-time pipeline updates
* Skeleton loading *(design includes shimmer bars; not yet wired to a live "running" state)*
* Progressive rendering
* Offline support

---

### Phase 10 — Enterprise Features  ⚪ Later

* User authentication
* OAuth
* Multi-tenancy
* Organization workspaces
* Billing
* Subscription plans
* API access
* Audit logging
* Admin dashboard

---

### Phase 11 — Deployment & Infrastructure  ⚪ Later

* Docker Compose
* Kubernetes
* CI/CD pipelines
* GitHub Actions
* Monitoring
* Prometheus
* Grafana
* Centralized logging
* Automated backups
* Horizontal scaling

---

### Phase 12 — AI Enhancements  ⚪ Later

* Long-term memory
* Self-reflection
* Multi-step reasoning
* Automatic planning
* Tool selection
* Autonomous retries
* Multi-modal research
* Voice research assistant
* Image understanding
* Code understanding

---

## 17. Implementation Status

> Quick-reference snapshot. The narrative baseline is §15 (Current Scope & Known Limitations); the forward plan is §16.

### ✅ Implemented

* FastAPI backend
* React frontend
* Multi-step research pipeline
* Research planning
* Web search (Tavily)
* HTML scraping
* Source cleaning
* Source deduplication
* Citation numbering
* Source reliability classification
* LLM synthesis
* Research evaluation
* SQLite persistence
* Research history
* Responsive dashboard
* Gemini/OpenAI compatibility

---

### 🚧 In Progress

* Improved planning prompts
* Better source evaluation
* Enhanced synthesis quality
* More robust error handling
* Expanded testing

---

### 📋 Planned

* Academic databases
* Vector database
* RAG pipeline
* PDF processing
* Multi-agent workflow
* Citation export
* Report export
* Authentication
* Project workspaces
* Collaboration
* Knowledge graph
* Analytics dashboard
* Streaming execution
* Parallel execution
* AI memory
* Research chat
* Native mobile app / PWA *(web UI is already responsive — see §11)*

---

## 18. Long-Term Vision

Research Console aims to evolve into a fully autonomous AI research platform capable of performing end-to-end research with minimal human intervention.

The long-term objectives include:

* Autonomous research planning
* Deep web and academic research
* Multi-agent collaboration
* Self-verification of generated content
* Explainable AI reasoning
* Human-in-the-loop review
* Production-grade scalability
* Enterprise deployment
* Academic research assistance
* Business intelligence generation
* Personalized research memory
* Continuous learning through user feedback

The ultimate vision is to provide an AI system that functions as a reliable digital research assistant capable of searching, analyzing, verifying, synthesizing, and presenting high-quality research with transparent citations, measurable confidence, and explainable reasoning.
