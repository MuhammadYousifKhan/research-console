# 🔬 Research Console — Autonomous AI Research Agent

> Turn a single research question into a **cited, evaluated answer** — with a transparent, multi-step agent pipeline you can watch end to end.

Research Console is a full-stack application that automates the research loop: it **plans** research tasks, **searches & scrapes** sources, **cleans & classifies** evidence, **synthesizes** a cited answer, and **evaluates** whether that answer is actually supported by the evidence. Every run — tasks, pipeline steps, sources, answer, and support evaluation — is surfaced in a responsive React dashboard.

A core design principle is **honest state reporting**: the console never fakes a result. Tool failures, LLM failures, and low-confidence evaluations are shown explicitly instead of being hidden.

---

## 📑 Table of Contents

- [Features](#-features)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [The Agent Pipeline](#-the-agent-pipeline)
- [Project Structure](#-project-structure)
- [API Reference](#-api-reference)
- [Setup & Installation](#-setup--installation)
- [Running the App](#-running-the-app)
- [Configuration](#-configuration)
- [Design System](#-design-system)
- [Roadmap & Future Implementations](#-roadmap--future-implementations)
- [Contributing](#-contributing)

---

## ✨ Features

### Implemented today
- 🧠 **Autonomous research planning** — decomposes a query into prioritized, tool-ready tasks (with a heuristic fallback if the LLM fails).
- 🔎 **Live web search** via [Tavily](https://tavily.com) + **HTML scraping** of arbitrary URLs.
- 🎓 **Academic search** — free, key-less [arXiv](https://arxiv.org) and [Semantic Scholar](https://www.semanticscholar.org) tools; the planner routes scientific/technical queries to them and tags results as high-reliability academic sources (authors + year + abstract).
- ⚡ **Parallel tool execution** — all of a plan's tool calls run concurrently (`asyncio.gather`), preserving order; one failure never aborts the run.
- 🧹 **Evidence cleanup** — text normalization, URL-based deduplication, and numbered citation assignment.
- 🏷️ **Source credibility classification** — domain heuristics tag each source by type (academic, government, news, industry, organization) and reliability (high / medium / low / unknown).
- 🧠 **RAG retrieval** — gathered evidence is chunked, embedded into a per-run **Chroma** vector index (local MiniLM model, no API key), and only the **top-k most query-relevant, citation-tagged chunks** are fed to synthesis. Falls back to full evidence if retrieval is unavailable.
- ✍️ **Cited synthesis** — generates a structured answer using **only** the gathered (retrieved) evidence, with inline `[n]` citations.
- ✅ **Support evaluation** — a dedicated evaluator checks whether the answer is supported, returns a confidence level, and lists missing evidence.
- 📚 **Citation export** — every source rendered in **APA, MLA, IEEE, Harvard, Chicago, and BibTeX**, with per-reference and "copy all" buttons. Deterministic (no LLM). Academic sources (arXiv / Semantic Scholar) cite real **authors and publication year**; web sources fall back to web-resource style with an accessed date.
- 📡 **Live streaming progress** — `POST /research/stream` emits each pipeline stage as a **Server-Sent Event**, so the sidebar pipeline fills in stage-by-stage instead of waiting on a spinner. The same pipeline backs the plain `POST /research`.
- 💾 **Persistence & history** — every run is stored (SQLite) and browsable from the dashboard.
- 🔁 **Failure isolation** — a single tool or LLM failure degrades only that stage; the run always returns a partial, honestly-labeled result.
- 🤖 **Dual LLM support** — works with any **OpenAI-compatible** API **or** **Google Gemini** (currently configured for Gemini 2.5 Flash).
- 🎨 **Responsive dashboard** — the "Instrument" dark theme with a numbered pipeline, metric cards, source grid, and honest empty/error/loading states.

### Planned (see [Roadmap](#-roadmap--future-implementations))
More academic source APIs (PubMed, CrossRef, Google Scholar), CrossRef DOI enrichment for web sources, persistent cross-run + hybrid RAG retrieval, document intelligence (PDF/DOCX), report export (PDF/DOCX bundle), multi-agent orchestration, workspaces, collaboration, analytics, and more.

---

## 🏗 Architecture

```
                          ┌───────────────────────────────────────────────┐
   POST /research         │                  FastAPI app                   │
  { query, max_tasks } ──▶│                                                │
                          │  Planner ▶ Executor ▶ Cleanup ▶ Retrieval ▶ Synth│▶ Evaluator
                          │     │          │          │          │        │  │     │
                          │     │          ▼          ▼          ▼        ▼  │     ▼
                          │     │    Tools(search,  dedupe +  top-k     cited│  support +
                          │     │     scrape)       classify  chunks    answer  confidence
                          │     ▼                            (Chroma)        │
                          │  task list                                      │
                          └───────────────────────┬───────────────────────┘
                                                   │  persist full run (SQLite)
                                                   ▼
                                          GET /research       (history)
                                          GET /research/{id}  (full run)
                                                   │
                                                   ▼
                                       React dashboard (RTK Query)
```

The pipeline is **linear and sequential**, producing one named `ExecutionStep` per stage (`completed` or `failed`). Each stage is failure-isolated so the run never aborts midway.

---

## 🛠 Tech Stack

### Backend
| Concern | Technology |
|---|---|
| Language | Python 3.12 (3.11+ supported) |
| Web framework | FastAPI |
| ASGI server | Uvicorn |
| Validation / schemas | Pydantic v2 + pydantic-settings |
| HTTP client | httpx (async) |
| HTML parsing | BeautifulSoup4 |
| ORM / DB | SQLAlchemy 2.0 + SQLite |
| Vector DB / embeddings | Chroma (per-run, in-memory) + local MiniLM ONNX |
| Testing | pytest + pytest-asyncio |

### Frontend
| Concern | Technology |
|---|---|
| Language | TypeScript |
| UI library | React 19 |
| Build tool | Vite |
| State & data fetching | Redux Toolkit + RTK Query |
| Styling | Hand-written CSS with design tokens |
| Fonts | Geist, JetBrains Mono |
| Linting | ESLint + typescript-eslint |

### External services
| Service | Purpose | Required? |
|---|---|---|
| LLM API (OpenAI-compatible **or** Google Gemini) | Planning, synthesis, evaluation | ✅ Yes |
| Tavily | Live web search | ⛅ Optional (degrades gracefully) |
| arXiv / Semantic Scholar | Academic paper search | 🆓 No key required |

---

## 🤝 The Agent Pipeline

| Stage | Agent / Service | What it does | Fallback |
|---|---|---|---|
| 1. Planning | `ResearchPlanner` | Query → ≤ `max_tasks` tool-ready tasks (strict JSON) | Heuristic background + risks plan |
| 2. Tool execution | `ResearchExecutor` | Runs each task's tool, captures observations | Per-task error capture (run continues) |
| 3. Cleanup | `ResearchCleanupService` | Normalize text, dedupe by URL, classify sources, number citations | — |
| 4. Retrieval | `RAGRetriever` | Chunk + embed evidence into a per-run Chroma index; keep top-k citation-tagged chunks for synthesis | Falls back to full evidence (step marked `failed`) |
| 5. Synthesis | `ResearchSynthesizer` | Cited answer from the retrieved evidence | Transparent placeholder answer |
| 6. Evaluation | `ResearchEvaluator` | `is_supported`, `confidence`, `missing_evidence`, `notes` | Heuristic evaluation from evidence presence |

**Tools** (in `backend/app/tools/`):
- `search_web` — Tavily search (basic depth, 5 results); returns a "not configured" notice if `TAVILY_API_KEY` is missing.
- `search_arxiv` — free, key-less arXiv Atom API (5 results); high-reliability academic sources.
- `search_scholar` — free, key-less Semantic Scholar Graph API (5 results); reports HTTP 429 rate-limiting honestly.
- `scrape_page` — fetches a URL, parses with BeautifulSoup, extracts readable `<p>` text (capped at 3000 chars).

> This is a hand-rolled multi-agent setup (no LangChain/LangGraph yet) whose executor runs tool calls in parallel and whose synthesis is RAG-backed (per-run Chroma index). The [roadmap](#-roadmap--future-implementations) extends it into specialized agents with persistent retrieval.

---

## 📂 Project Structure

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
│   │   │   ├── search_arxiv.py     # arXiv preprint search (Atom/XML)
│   │   │   ├── search_scholar.py   # Semantic Scholar search (JSON)
│   │   │   └── scrape_page.py      # URL → readable text
│   │   ├── services/
│   │   │   ├── llm.py              # OpenAI/Gemini client
│   │   │   ├── pipeline.py         # async-generator pipeline orchestration
│   │   │   ├── rag.py              # chunk + embed + retrieve (Chroma, per-run)
│   │   │   ├── citations.py        # 6-style citation formatter
│   │   │   └── research_cleanup.py # dedupe, classify, cite
│   │   ├── memory/research_memory.py
│   │   ├── schemas/research.py     # Pydantic models
│   │   ├── models/research_run.py  # SQLAlchemy ORM model
│   │   ├── core/{config,database}.py
│   │   └── main.py                 # FastAPI app + pipeline orchestration
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── app/{store,hooks}.ts            # Redux store + typed hooks
│   │   ├── features/research/             # RTK Query API, UI slice, TS types
│   │   ├── components/
│   │   │   ├── layout/                    # Header, Sidebar, Footer
│   │   │   └── research/                  # Form, History, Workspace, Timeline,
│   │   │                                  #   Sources, Answer, Empty, Error
│   │   ├── utils/format.ts
│   │   ├── App.tsx / App.css / index.css  # "Instrument" design
│   │   └── main.tsx
│   ├── vite.config.ts                     # dev port pinned to 5173
│   └── package.json
│
├── package.json                           # root dev scripts
├── spec.md                                # full project specification
└── README.md
```

---

## 🔌 API Reference

Base URL (dev): `http://127.0.0.1:8000` · Interactive docs: `http://127.0.0.1:8000/docs`

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check → `{ "status": "ok" }` |
| `POST` | `/research` | Run the full pipeline; persists and returns the complete result |
| `POST` | `/research/stream` | Run the pipeline and stream each stage as **Server-Sent Events** (`step` × 6 → `complete`); `text/event-stream` |
| `GET` | `/research?limit=N` | List recent run summaries (newest first, limit 1–100) |
| `GET` | `/research/{id}` | Fetch one full run (`404` if not found) |
| `GET` | `/research/{id}/citations` | Citations for the run's sources in all 6 styles + accessed date (`404` if not found) |

<details>
<summary><strong>Example — <code>POST /research</code></strong></summary>

**Request**
```json
{ "query": "What is the scientific consensus on direct air capture at scale?", "max_tasks": 6 }
```

**Response (abridged)**
```json
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
</details>

---

## ⚙️ Setup & Installation

### Prerequisites
- **Python** 3.12 (3.11+ works)
- **Node.js** 18+ and **npm**
- An **LLM API key** (OpenAI-compatible or Google Gemini) — required
- A **Tavily API key** — optional, enables live web search

### 1. Clone
```bash
git clone https://github.com/MuhammadYousifKhan/research-console.git
cd research-console
```

### 2. Backend
```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt

# create your env file and fill in the keys
copy .env.example .env        # Windows
# cp .env.example .env         # macOS / Linux
```

Edit `backend/.env`:
```env
OPENAI_API_KEY=your_key_here
OPENAI_BASE_URL=https://generativelanguage.googleapis.com/v1beta   # Gemini (default)
OPENAI_MODEL=gemini-2.5-flash
TAVILY_API_KEY=your_tavily_key_here   # optional
```
> 💡 To use OpenAI instead of Gemini, set `OPENAI_BASE_URL=https://api.openai.com/v1` and `OPENAI_MODEL=gpt-4.1-mini` (or any model you have access to).

### 3. Frontend
```bash
cd ../frontend
npm install
```

### 4. Root tooling (optional, runs both at once)
```bash
cd ..
npm install
```

---

## ▶️ Running the App

### Option A — everything at once (from repo root)
```bash
npm run dev
```
Starts the **backend on `http://127.0.0.1:8000`** and the **frontend on `http://localhost:5173`** together.

### Option B — separately
```bash
# Terminal 1 — backend
npm run dev:backend
# (or: cd backend && uvicorn app.main:app --reload --port 8000)

# Terminal 2 — frontend
npm run dev:frontend
# (or: cd frontend && npm run dev)
```

### Build & test
```bash
npm run build:frontend   # type-check + production build
npm run test:backend     # pytest
```

| Script | What it does |
|---|---|
| `npm run dev` | Backend + frontend together (via `concurrently`) |
| `npm run dev:backend` | Uvicorn with autoreload on port 8000 |
| `npm run dev:frontend` | Vite dev server on port 5173 |
| `npm run build:frontend` | `tsc -b && vite build` |
| `npm run test:backend` | Run the pytest suite |

---

## 🔧 Configuration

### Backend (`backend/.env`)
| Variable | Default | Purpose |
|---|---|---|
| `APP_NAME` | "Autonomous Research AI Agent" | App title |
| `APP_ENV` | development | Environment label |
| `DATABASE_URL` | `sqlite:///./research.db` | DB connection string |
| `OPENAI_API_KEY` | _(empty)_ | LLM key — **required** |
| `OPENAI_BASE_URL` | Gemini base URL | Switches LLM provider (OpenAI vs Gemini) |
| `OPENAI_MODEL` | `gemini-2.5-flash` | Model id |
| `TAVILY_API_KEY` | _(empty)_ | Enables live web search |
| `CORS_ALLOW_ORIGINS` | localhost/127.0.0.1 :5173–5175 | Allowed frontend origins |

### Frontend (`frontend/.env`, optional)
| Variable | Default | Purpose |
|---|---|---|
| `VITE_API_BASE_URL` | `http://127.0.0.1:8000` | Backend API base URL |

> ⚠️ **Never commit real API keys.** `backend/.env` is gitignored. Rotate any key that has been shared.

---

## 🎨 Design System

The UI implements the **"Instrument"** theme — a dark, instrument-panel aesthetic with an amber/gold accent.

| Token | Value |
|---|---|
| Page / Shell / Panel | `#0b0c0d` / `#131517` / `#181a1d` |
| Accent | `#e8a13c` (amber) |
| OK / Fail / Medium | `#5ec98a` / `#e8593f` / `#e8a13c` |
| Fonts | Geist (UI), JetBrains Mono (labels) |

**Responsive behavior:** centered shell (max 1320px) → pipeline-beside-answer grid that stacks ≤1180px → sidebar collapses to a slide-in drawer ≤980px → single column ≤680px.

---

## 🗺 Roadmap & Future Implementations

The full, phased roadmap (with dependencies and a recommended build order) lives in [`spec.md`](spec.md). Highlights:

| Phase | Theme | Status |
|---|---|---|
| 1 | **Research Intelligence** — arXiv ✅, Semantic Scholar ✅; next: PubMed, GitHub, semantic search, query expansion | 🟢 Started |
| 2 | **Multi-Agent Architecture** — Analysis & Reviewer agents; LangGraph orchestration (Citation export ✅ done) | 🟢 Started |
| 3 | **RAG** — per-run chunking + embeddings + Chroma vector index + citation-aware top-k retrieval ✅; next: persistent cross-run store, hybrid retrieval | 🟢 Started |
| 4 | **Document Intelligence** — PDF/DOCX upload, OCR, table/figure/citation extraction, doc chat | ⚪ Later |
| 5 | **Research Workspace** — projects, folders, tags, collections, notes | ⚪ Later |
| 6 | **Collaboration** — shared workspaces, roles, comments, live editing | ⚪ Later |
| 7 | **Analytics & Visualization** — citation networks, knowledge graphs, timelines | ⚪ Later |
| 8 | **AI Memory** — persistent cross-run preferences & history | ⚪ Later |
| 9 | **Performance** — parallel/async execution ✅, streaming progress (SSE) ✅; next: caching | 🟢 Started |
| 10 | **Enterprise** — auth, OAuth, multi-tenancy, billing, audit logs | ⚪ Later |
| 11 | **Deployment** — Docker, Kubernetes, CI/CD, monitoring | ⚪ Later |
| 12 | **AI Enhancements** — long-term memory, self-reflection, multi-modal, voice | ⚪ Later |

**Recommended near-term build order:** parallelize the executor ✅ → academic search tools ✅ → citation export ✅ → streaming progress ✅ → RAG pipeline ✅ → document intelligence (next). See [`spec.md` §16](spec.md) for the detailed table.

---

## 🤝 Contributing

1. Fork the repo and create a feature branch (`git checkout -b feature/my-feature`).
2. Make your changes; keep the **honest-state** principle (never fake results or hide failures).
3. Run `npm run build:frontend` and `npm run test:backend` before opening a PR.
4. Open a pull request describing the change.

---

## 📄 License

No license file is currently included. Add one (e.g., MIT) before public distribution.

---

<div align="center">

**Research Console** · Built with FastAPI + React · See [`spec.md`](spec.md) for the full specification.

</div>
