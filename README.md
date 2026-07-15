# Customer Support System

An AI-powered customer support ticket processing pipeline. Tickets are validated, screened for
prompt injection, language-detected, classified, drafted, and independently confidence-scored by
an LLM pipeline built with **LangGraph**, exposed through a **FastAPI** backend, backed by
**PostgreSQL**, and reviewed through an internal **Streamlit** dashboard. All LLM calls go through
**OpenRouter** via the OpenAI-compatible SDK, so any pipeline model can be swapped via config with
no code changes.

## Architecture

```
POST /tickets
      │
      ▼
┌─────────────┐   reject    ┌──────────────────────┐
│  1. Validate │────────────▶│  8. Log/Persist      │──▶ logs table only
│  (regex)     │            │  (no ticket row)      │    (ticket NOT saved)
└─────┬───────┘             └──────────────────────┘
      │ ok
      ▼
┌─────────────────────┐  injection   ┌──────────────────────┐
│ 2. Injection check    │────────────▶│  8. Log/Persist      │──▶ logs table only
│    (cheap LLM)         │            │  (no ticket row)      │
└─────┬───────────────┘              └──────────────────────┘
      │ clean
      ▼
┌─────────────────────┐
│ 3. Language detection │  fasttext lid.176 primary; LLM fallback if confidence < 0.7
└─────┬───────────────┘
      ▼
┌─────────────────────┐
│ 4. Classify + draft    │  cheap/fast model → category, priority, summary, draft_reply
└─────┬───────────────┘
      │ (skip judge if this step failed after retries)
      ▼
┌─────────────────────┐
│ 5. Confidence eval     │  stronger model, independent judge → confidence_score 0-100
└─────┬───────────────┘
      ▼
┌─────────────────────┐
│ 6. Confidence router   │  >= threshold → auto_ready · < threshold → manual_review
└─────┬───────────────┘
      ▼
┌─────────────────────┐
│ 8. Log/Persist         │  writes ticket row + all step-level logs
└─────────────────────┘
```

Every LLM-calling node (2, 3's fallback, 4, 5) retries up to `MAX_LLM_RETRIES` (default 3) times
total on failure. If a node still fails after retries, the ticket falls through to
`manual_review` with the error recorded in `logs` — it is **not** silently dropped, and the
draft reply is generated whenever the classification step itself succeeds, regardless of the
confidence score.

## Project layout

```
app/
  config.py           # env-driven settings, including per-step model IDs
  database.py          # async engine (API reads) + sync engine (pipeline writes)
  security.py           # X-API-Key dependency
  rate_limit.py          # slowapi limiter
  main.py                 # FastAPI app
  models/
    db_models.py           # SQLAlchemy Ticket / Log tables
    schemas.py               # Pydantic request/response models
  pipeline/
    validators.py             # step 1 — deterministic regex checks
    language_detect.py         # step 3 — fasttext
    llm_client.py                # OpenRouter client + JSON parsing helpers
    retry.py                      # shared retry harness
    nodes.py                       # steps 2, 3, 4, 5, 6, 8 as LangGraph nodes
    state.py                        # TicketState TypedDict
    graph.py                         # wires nodes into the LangGraph StateGraph
  routes/
    tickets.py                       # POST/GET endpoints
dashboard/
  app.py                                # Streamlit internal dashboard
migrations/                              # Alembic
```

## Environment variables

Copy `.env.example` to `.env` and fill in real values — **never commit `.env`**.

| Variable | Required | Description |
|---|---|---|
| `API_KEY` | yes | Shared secret clients must send in `X-API-Key` |
| `DATABASE_URL` | yes | Postgres connection string (`postgresql://...`) |
| `OPENROUTER_API_KEY` | yes | OpenRouter API key |
| `OPENROUTER_BASE_URL` | no | Defaults to `https://openrouter.ai/api/v1` |
| `INJECTION_CHECK_MODEL` | no | Cheap model for step 2 (default `openai/gpt-4o-mini`) |
| `CLASSIFICATION_MODEL` | no | Cheap/fast model for step 4 (default `openai/gpt-4o-mini`) |
| `CONFIDENCE_MODEL` | no | Stronger judge model for step 5 (default `anthropic/claude-sonnet-4.5` — check [openrouter.ai/models](https://openrouter.ai/models) for the current slug) |
| `LANGUAGE_FALLBACK_MODEL` | no | Model for step 3's LLM fallback |
| `CONFIDENCE_THRESHOLD` | no | Auto-ready cutoff, default `70` |
| `MAX_LLM_RETRIES` | no | Total attempts per LLM node, default `3` |
| `FASTTEXT_CONFIDENCE_THRESHOLD` | no | Below this, fall back to LLM language detection. Default `0.7` |
| `FASTTEXT_MODEL_PATH` | no | Where to cache the downloaded `lid.176.ftz` model |
| `MIN_TICKET_LENGTH` / `MAX_TICKET_LENGTH` | no | Validation bounds, default `3` / `10000` |
| `RATE_LIMIT` | no | slowapi rate limit string, default `10/minute` |
| `BACKEND_API_URL` | dashboard only | URL of the FastAPI backend |
| `DASHBOARD_API_KEY` | dashboard only | Same value as `API_KEY` — kept as a separate var so it's clear this is the dashboard's own credential, never exposed to whoever views the dashboard |

## Running locally

### 1. Postgres

Use a local instance or Docker:

```bash
docker run --name cst-postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=tickets -p 5432:5432 -d postgres:16
```

### 2. Install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
# edit .env: set API_KEY, DATABASE_URL, OPENROUTER_API_KEY, DASHBOARD_API_KEY
```

### 4. Run migrations

```bash
alembic upgrade head
```

### 5. Start the backend

```bash
uvicorn app.main:app --reload --port 8000
```

The first ticket submission will download the fasttext `lid.176.ftz` language ID model
(~1MB) into `models/` if it isn't already present.

### 6. Start the dashboard (separate terminal)

```bash
streamlit run dashboard/app.py
```

Set `BACKEND_API_URL` and `DASHBOARD_API_KEY` in `.env` (or the shell) before starting it — the
dashboard reads its API key from its own environment and never exposes it to the browser.

## Testing the API

```bash
# Submit a ticket
curl -X POST http://localhost:8000/tickets \
  -H "Content-Type: application/json" \
  -H "X-API-Key: change-me-to-a-long-random-string" \
  -d '{"raw_text": "I was charged twice for my subscription this month and need a refund for the duplicate charge."}'

# List tickets
curl http://localhost:8000/tickets \
  -H "X-API-Key: change-me-to-a-long-random-string"

# Get one ticket's detail + logs
curl http://localhost:8000/tickets/<ticket-id> \
  -H "X-API-Key: change-me-to-a-long-random-string"
```

A rejected ticket (too short, repetitive, or a detected prompt injection attempt) returns
`{"id": null, "accepted": false, "message": "<reason>"}` and is logged but never written to the
`tickets` table.

Run the unit tests:

```bash
pytest
```

## Deploying to Railway

This repo deploys as **two Railway services** from the same GitHub repo: the FastAPI backend and
the Streamlit dashboard.

1. **Create a new Railway project** from this repo, and add a **PostgreSQL** plugin — Railway
   injects `DATABASE_URL` automatically for services you attach it to.
2. **Backend service** (uses the root `railway.json`, start command
   `uvicorn app.main:app --host 0.0.0.0 --port $PORT`):
   - Set `API_KEY`, `OPENROUTER_API_KEY`, and any model overrides as environment variables.
   - Reference the Postgres plugin's `DATABASE_URL` variable.
   - After the first deploy, run migrations: `railway run alembic upgrade head`.
3. **Dashboard service** — add a second service from the same repo:
   - In the service's Settings, either set a **Custom Start Command** to
     `streamlit run dashboard/app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true`,
     or point its config-as-code path at `railway.dashboard.json`.
   - Set `BACKEND_API_URL` to the backend service's public Railway URL.
   - Set `DASHBOARD_API_KEY` to the same value as the backend's `API_KEY`.
4. Confirm both services are green, then hit the backend's `/health` endpoint and the
   dashboard's public URL.

## Notes on the pipeline design

- **Rejected tickets are never persisted to `tickets`** — only to `logs`, with `ticket_id = NULL`,
  per the validation and injection-check requirements.
- **`logs.ticket_id` is nullable** for exactly this reason.
- **Retry accounting**: `tickets.retry_count` is the sum of extra attempts (beyond the first)
  spent across every LLM-calling node for that ticket.
- **Model swapping**: every model used by the pipeline is an env var (see table above) — change
  it and redeploy, no code edits required.
