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

## Sample Results

### Async smoke output

```text
(ai_venv_py3.14) adelmahmoud@adels-mbp invirto_capital_task % python3 ./scripts/async_smoke_test.py
[SMOKE] Prompt: Analyze the company whose ticker GOOGL. Return only JSON.
[SMOKE] App sent API request: POST /analysis
[SMOKE] Job created: job_id=3aa014a1-4831-463d-b85f-edebb2ac3eb3
[SMOKE] Polling job status...
[SMOKE] Poll #1: status=QUEUED progress=0
[SMOKE] Poll #2: status=RUNNING progress=5
[SMOKE] Poll #3: status=RUNNING progress=5
[SMOKE] Poll #4: status=RUNNING progress=5
[SMOKE] Poll #5: status=RUNNING progress=5
[SMOKE] Poll #6: status=RUNNING progress=5
[SMOKE] Poll #7: status=RUNNING progress=5
[SMOKE] Poll #8: status=RUNNING progress=5
[SMOKE] Poll #9: status=SUCCEEDED progress=100
[SMOKE] Terminal status reached: SUCCEEDED
[SMOKE] Fetching final result...
[SMOKE] GET /analysis/{job_id}/result -> 200
[SMOKE] Result payload:
{'company': 'Alphabet Inc.', 'thesis': "Alphabet Inc. continues to demonstrate strong financial performance with a net income margin of 32.8% and a market capitalization of approximately $3.72 trillion. The company's diverse revenue streams from Google Services, Google Cloud, and Other Bets segments position it well for future growth. Recent advancements in automation technology, such as the Gemini project, indicate a commitment to innovation in its product offerings. However, the competitive landscape in the tech industry remains a challenge.", 'signal': 'Bullish', 'insights': ['Market capitalization stands at approximately $3.72 trillion.', 'Latest revenue reported at $402.96 billion with a net income of $132.17 billion.', 'P/E ratio is 28.08, indicating a relatively high valuation.', 'Gross margin is 59.7%, showcasing strong profitability.', 'Recent news highlights advancements in automation with the Gemini project, enhancing user experience on Android.'], 'sources': ['https://financialmodelingprep.com/stable/profile?symbol=GOOGL', 'https://financialmodelingprep.com/stable/income-statement?symbol=GOOGL&limit=1', 'http://9to5google.com/2026/02/25/android-appfunctions-gemini/']}
```

### Worker step tracing

```text
[STEP] Worker consumed job (job_id=3aa014a1-4831-463d-b85f-edebb2ac3eb3)
[STEP] Worker sent prompt to agent (job_id=3aa014a1-4831-463d-b85f-edebb2ac3eb3)
[STEP] Agent received prompt (job_id=3aa014a1-4831-463d-b85f-edebb2ac3eb3)
[STEP] Agent started iterations with 2 tools
[STEP] Tool call detected: get_company_snapshot args={"ticker": "GOOGL"}
[STEP] Tool call detected: get_recent_news args={"query": "Google OR GOOGL", "page_size": 20, "days_back": 14}
[STEP] Tool call result: get_company_snapshot -> { "ticker": "GOOGL", "name": "Alphabet Inc.", "sector": "Technology", "industry": "Internet Content & Information", "description": "Alphabet Inc. provides various products and platforms in the United States, Europe, t...
[STEP] Tool call result: get_recent_news -> { "query": "Google OR GOOGL", "from": "2026-02-13", "articles": [ { "title": "Gemini can now automate some multi-step tasks on Android - TechCrunch", "description": "Gemini can now automate some multi-step tasks on An...
[STEP] Agent iterations: 2
[STEP] Result stored in database (job_id=3aa014a1-4831-463d-b85f-edebb2ac3eb3)
```

## Common Failure Modes

- Missing `OPENAI_API_KEY`: agent startup fails immediately
- Missing `FMP_API_KEY` or `NEWS_API_KEY`: MCP tool calls fail at runtime
- Redis not running: job enqueue/worker processing fails
- Polling result before completion: `/result` returns `409`
