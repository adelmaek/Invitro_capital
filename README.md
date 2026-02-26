# MCP Financial + News Servers

Two Python MCP servers (stdio transport) exposing tools for:
- Structured company fundamentals via Financial Modeling Prep (FMP)
- Unstructured recent news via NewsAPI

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

```bash
cp .env.example .env
```

## Run Servers (stdio)

```bash
python -m mcp_servers.fmp_server
```

```bash
python -m mcp_servers.news_server
```

## Local Tool Test (direct function calls)

```bash
python scripts/test_mcp_tools.py
```

## Agent Smoke Test (LangChain + MCP)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python scripts/run_agent_smoke_test.py
```

## Agent Module 

The project now includes a minimal modular agent package in `agent/` that:
- Loads configuration from `.env` (`OPENAI_API_KEY`, `OPENAI_MODEL`)
- Starts both MCP servers and discovers tools
- Builds a LangChain 1.x tool-calling agent (`langchain.agents.create_agent`)
- Runs analysis for a ticker and returns only the final JSON string
- Shuts down MCP sessions after each run

### Current agent flow

1. `agent.config.get_settings()` loads environment settings
2. `agent.toolkit.create_toolkits()` starts MCP sessions for:
   - `mcp_servers.fmp_server`
   - `mcp_servers.news_server`
3. `agent.factory.create_agent()` creates the OpenAI + tools agent
4. `agent.service.run_analysis(ticker)` executes the agent and returns JSON output
5. MCP sessions are stopped in `finally` (per-run lifecycle, no shared global state)

### Package layout

- `agent/config.py`: settings loading
- `agent/mcp_session.py`: explicit MCP lifecycle (`start` / `stop`)
- `agent/toolkit.py`: combine MCP tools from both servers
- `agent/prompts.py`: system message (agent instructions)
- `agent/factory.py`: build LangChain agent executor
- `agent/service.py`: orchestration (`run_analysis`)

### Smoke test behavior

`scripts/run_agent_smoke_test.py`:
- Calls `run_analysis("AAPL")`
- Prints the returned output
- Validates JSON parsing
- Validates required keys:
  - `company`, `thesis`, `signal`, `insights`, `sources`
- Prints `SMOKE TEST PASSED` on success

It also enables INFO logs so you can see which module steps were invoked (settings load, MCP startup, tool discovery, agent creation, execution, teardown).

### Important note

The smoke test requires outbound network access for:
- OpenAI API (agent model call)
- FMP API (financial data)
- NewsAPI (news fetch)

## Endpoints Used

FMP:
- `GET {FMP_BASE_URL}/profile?symbol={ticker}&apikey={FMP_API_KEY}`
- `GET {FMP_BASE_URL}/ratios-ttm?symbol={ticker}&apikey={FMP_API_KEY}`
- `GET {FMP_BASE_URL}/income-statement?symbol={ticker}&limit=1&apikey={FMP_API_KEY}`

NewsAPI:
- `GET {NEWS_BASE_URL}/v2/everything`
  - `q={query}`
  - `sortBy=publishedAt`
  - `pageSize={page_size}`
  - `language={language}`
  - `from={ISO_DATE}`
  - `apiKey={NEWS_API_KEY}`
