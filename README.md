# Invitro Capital Task

Python service stack for running prompt-based investment analysis with:
- MCP tool servers for market data and news
- A LangChain/OpenAI agent that calls those tools
- FastAPI endpoints for async job execution
- Celery worker + Redis queue
- SQLAlchemy-backed job persistence

## What This Repo Does

The system accepts a natural-language prompt (for example `Analyze the company whose ticker GOOGL and return only JSON`), then the agent extracts a ticker and calls:
1. FMP fundamentals MCP tool (`mcp_servers.fmp_server`)
2. News MCP tool (`mcp_servers.news_server`)

Then stores the final JSON analysis as a job result retrievable via API.

## Architecture

- API layer: `app/`
- Background execution: `worker/`
- Agent orchestration: `agent/`
- MCP tool servers: `mcp_servers/`
- Smoke tests / local checks: `scripts/`

Data flow:
1. `POST /analysis` creates job in DB (`QUEUED`)
2. API enqueues Celery task (`worker.run_analysis_task`)
3. Worker loads job input (`prompt`), runs `agent.service.run_analysis(prompt=...)`
4. Agent starts MCP sessions, calls tools, returns JSON string
5. Worker persists result and marks job `SUCCEEDED` or `FAILED`
6. Client polls status and reads result

## Requirements

- Python 3.11+
- Redis (for Celery broker/backend)
- API keys for OpenAI, Financial Modeling Prep, and NewsAPI

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set real values in `.env`.

## Environment Variables

Required for full end-to-end run:

- `OPENAI_API_KEY`
- `FMP_API_KEY`
- `NEWS_API_KEY`

Optional (defaults shown):

- `OPENAI_MODEL=gpt-4o-mini`
- `FMP_BASE_URL=https://financialmodelingprep.com/stable`
- `NEWS_BASE_URL=https://newsapi.org`
- `HTTP_TIMEOUT_SECONDS=20`
- `DATABASE_URL=sqlite:///./jobs.db`
- `REDIS_URL=redis://localhost:6379/0`

See `.env.example` for the canonical template.

## How To Run

### 1) Run API + Worker stack

Terminal A (Redis):
```bash
redis-server
```

Terminal B (FastAPI):
```bash
uvicorn app.main:app --reload
```

Terminal C (Celery worker):
```bash
celery -A worker.celery_app.celery worker --loglevel=WARNING
```

### 2) Run async API smoke test (recommended path)

```bash
python scripts/async_smoke_test.py
```

## API Contract

### `POST /analysis`

Request body:
- `prompt` (string, required, non-empty, max 1000 chars)

Response:
- `{"job_id": "<uuid>"}`

### `GET /analysis/{job_id}`

Returns job metadata:
- `job_id`, `status`, `progress`, `error`, `created_at`, `updated_at`

### `GET /analysis/{job_id}/result`

- `200` with final analysis JSON when job is `SUCCEEDED`
- `409` while job is not complete (`QUEUED`/`RUNNING`)
- `409` with error payload when job is `FAILED`

## Main Modules

### `agent/`

- `config.py`: loads and validates runtime settings
- `mcp_session.py`: MCP session lifecycle helpers
- `toolkit.py`: starts MCP servers and discovers tools
- `prompts.py`: system prompt/instructions
- `factory.py`: builds LangChain agent executor
- `service.py`: one-shot analysis orchestration (`run_analysis`)

### `mcp_servers/`

- `fmp_server.py`: `get_company_snapshot(ticker)`
  - aggregates profile, ratios TTM, latest income statement
- `news_server.py`: `get_recent_news(query, page_size, days_back, language)`
  - fetches recent articles from NewsAPI
- `common.py`: env loading, HTTP client setup, shared helpers

### `app/`

- `main.py`: FastAPI app bootstrap + DB init on startup
- `api.py`: analysis job endpoints
- `db/engine.py`: SQLAlchemy engine/session setup
- `db/models.py`: `Job` ORM model
- `db/crud.py`: minimal job CRUD helpers

### `worker/`

- `celery_app.py`: Celery app + Redis broker/backend config
- `tasks.py`: background task entrypoint and result persistence

## Smoke Tests

Run these from repo root with virtualenv active.

### DB smoke test

```bash
python scripts/db_smoke_test.py
```

Validates table creation and CRUD updates for jobs.

### MCP tools smoke test (direct function calls)

```bash
python scripts/test_mcp_tools.py
```

Calls both MCP tool functions directly (requires FMP/News API access).

### Agent smoke test

```bash
python scripts/run_agent_smoke_test.py
```

Runs `run_analysis(prompt=...)` and validates required output JSON keys.

### Async API smoke test

Prereq: Redis + API + Celery running.

```bash
python scripts/async_smoke_test.py
```

Creates a job, polls status, and fetches final result.

## Common Failure Modes

- Missing `OPENAI_API_KEY`: agent startup fails immediately
- Missing `FMP_API_KEY` or `NEWS_API_KEY`: MCP tool calls fail at runtime
- Redis not running: job enqueue/worker processing fails
- Polling result before completion: `/result` returns `409`
