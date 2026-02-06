# Symbology

![Symbology Logo](https://i.imgur.com/v0cp4d1.png)

Explore LLM-generated insights on publicly traded companies. Symbology leverages company filings to identify trends and developments since the COVID-19 pandemic.

[symbology.online](https://symbology.online)

## Acknowledgements

- [trade bots](https://store.steampowered.com/app/1899350/Trade_Bots_A_Technical_Analysis_Simulation/)
- [investopedia](https://www.investopedia.com/)
- [edgartools](https://github.com/dgunning/edgartools)


---

## Background Jobs

Symbology includes a PostgreSQL-native background job queue for async processing of long-running tasks like data ingestion and content generation. No external broker (Redis, RabbitMQ) required — it uses `SELECT FOR UPDATE SKIP LOCKED` for atomic job claiming.

### Architecture

```
CLI / API  →  INSERT into jobs (status=PENDING)
                     ↓
Worker process  ←  SELECT ... FOR UPDATE SKIP LOCKED (poll loop)
                     ↓
               Execute handler function
                     ↓
               UPDATE status → COMPLETED or FAILED (with retry)
```

### Job Types

| Type | Description | Required Params |
|------|-------------|-----------------|
| `company_ingestion` | Fetch company data from SEC EDGAR | `ticker` |
| `filing_ingestion` | Ingest filings for a company | `company_id`, `ticker`; optional: `form`, `count`, `include_documents` |
| `content_generation` | Generate LLM content from sources | `system_prompt_hash`, `model_config_hash`; optional: `source_document_hashes`, `company_ticker` |
| `ingest_pipeline` | Full pipeline: company + filings | `ticker`; optional: `form`, `count`, `include_documents` |
| `test` | Echo handler for testing | any |

### Usage

**CLI:**

```bash
# Submit a job
just run-cli jobs submit company_ingestion -p '{"ticker": "AAPL"}'

# Full pipeline
just run-cli jobs submit ingest_pipeline -p '{"ticker": "MSFT", "form": "10-K", "count": 3}'

# Check status
just run-cli jobs status <job-id>

# List jobs
just run-cli jobs list --status pending
just run-cli jobs list --type company_ingestion

# Cancel a pending job
just run-cli jobs cancel <job-id>
```

**API:**

```bash
# Enqueue
curl -X POST /jobs/ -H 'Content-Type: application/json' \
  -d '{"job_type": "ingest_pipeline", "params": {"ticker": "AAPL"}, "priority": 1}'

# Get status
curl /jobs/<job-id>

# List with filters
curl '/jobs/?status=pending&job_type=company_ingestion'

# Cancel
curl -X DELETE /jobs/<job-id>
```

**Worker:**

```bash
# Start the worker process
just run-worker

# Configuration (environment variables)
WORKER_POLL_INTERVAL=2.0      # seconds between queue polls
WORKER_STALE_THRESHOLD=600    # seconds before a job is considered stale
WORKER_STALE_CHECK_INTERVAL=60  # seconds between stale-job sweeps
```

### LLM / Anthropic API

Content generation jobs use the Anthropic Claude API. You need an API key from [console.anthropic.com](https://console.anthropic.com/):

```bash
# Set in .env or export directly
export ANTHROPIC_API_KEY=sk-ant-...
```

The pipeline uses a 3-tier model structure:

| Stage | Model | Purpose |
|-------|-------|---------|
| Single summary | `claude-haiku-4-5-20251001` | Summarize individual filing documents |
| Aggregate summary | `claude-sonnet-4-5-20250929` | Combine single summaries |
| Frontpage summary | `claude-sonnet-4-5-20250929` | Generate final company overview |

### Priority & Retries

Jobs have a priority (0=critical, 4=backlog; default 2) and retry on failure up to `max_retries` (default 3). Stale jobs (in-progress but not updated within the threshold) are automatically recovered and re-queued.

---

● Symbology Codebase Review

  What it is: An LLM-powered financial research platform that ingests SEC EDGAR filings (10-K, 10-Q) and generates AI-synthesized insights — think automated equity research analyst.
  Live at symbology.online.

  Tech Stack Summary

  - Backend: Python 3.13, FastAPI, SQLAlchemy 2.0, PostgreSQL
  - Frontend: SvelteKit, TypeScript, Tailwind CSS, Bits UI
  - LLM: Anthropic Claude API (Haiku / Sonnet)
  - Infra: Caddy reverse proxy, Docker, just task runner
  - Data: SEC EDGAR via edgartools, XBRL financial extraction

  What's Working Well

  - Clean architecture — clear separation between API routes, database models, CLI, and ingestion pipeline
  - Structured logging with structlog throughout
  - Content hashing for deduplication and URL-addressable generated content
  - Modular CLI for ingestion and management (companies ingest, filings ingest, etc.)
  - Production deployment pipeline with Docker multi-stage builds and Caddy HTTPS

  Current Gaps (Prototype-Level)

  1. No authentication/authorization — fully open API
  2. No user accounts — can't personalize, save, or share anything
  3. No database migrations — using create_all() instead of Alembic
  4. Limited search — basic LIKE queries, no full-text search
  5. No caching layer — no Redis, repeated queries hit the DB every time
  6. No API rate limiting or versioning
  7. Thin test coverage — some DB tests, no E2E or comprehensive API tests
  8. ~~LLM tightly coupled to Ollama~~ — migrated to Anthropic Claude API
  9. No observability — no metrics/Prometheus, just logs
  10. Content is read-only — no way for users to interact with or act on insights

  ---
  Product Feature Ideas

  Here's how I'd think about the path from prototype to viable product, organized by priority:

  Tier 1: Core Product Value (Must-Have)
  ┌─────────────────────────┬────────────────────────────────────────────────────────────────────────────────┐
  │         Feature         │                                      Why                                       │
  ├─────────────────────────┼────────────────────────────────────────────────────────────────────────────────┤
  │ Watchlists / Portfolios │ Let users track companies they care about — this is the hook                   │
  ├─────────────────────────┼────────────────────────────────────────────────────────────────────────────────┤
  │ Alerts & Notifications  │ "New 10-K filed for AAPL" or "Risk factors changed significantly"              │
  ├─────────────────────────┼────────────────────────────────────────────────────────────────────────────────┤
  │ Comparative Analysis    │ Compare insights across companies, sectors, or time periods                    │
  ├─────────────────────────┼────────────────────────────────────────────────────────────────────────────────┤
  │ Improved Search         │ Full-text search across filings and generated content, sector/industry filters │
  ├─────────────────────────┼────────────────────────────────────────────────────────────────────────────────┤
  │ Fresh Data Pipeline     │ Automated ingestion of new filings as they appear on EDGAR                     │
  └─────────────────────────┴────────────────────────────────────────────────────────────────────────────────┘
  Tier 2: User Experience & Engagement
  ┌───────────────────────────────┬───────────────────────────────────────────────────────────────────────────────────────────────────┐
  │            Feature            │                                                Why                                                │
  ├───────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ User Accounts & Auth          │ Foundation for personalization, saved views, and monetization                                     │
  ├───────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ Interactive Q&A               │ Ask questions about a company's filings ("What are AAPL's main risk factors?")                    │
  ├───────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ Financial Data Visualizations │ Charts for revenue, margins, etc. from XBRL data (you already have LayerChart + financial_values) │
  ├───────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ Diff/Change Tracking          │ Highlight what changed between filings (e.g., new risk factors in latest 10-K)                    │
  ├───────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ Export & Sharing              │ PDF reports, shareable links, embed widgets                                                       │
  └───────────────────────────────┴───────────────────────────────────────────────────────────────────────────────────────────────────┘
  Tier 3: Monetization & Scale
  ┌────────────────────────────┬─────────────────────────────────────────────────────────────────────┐
  │          Feature           │                                 Why                                 │
  ├────────────────────────────┼─────────────────────────────────────────────────────────────────────┤
  │ Tiered Access / API Keys   │ Free tier with limits, paid tier for power users                    │
  ├────────────────────────────┼─────────────────────────────────────────────────────────────────────┤
  │ ~~Cloud LLM Support~~      │ ✅ Migrated to Anthropic Claude API (Haiku + Sonnet)                 │
  ├────────────────────────────┼─────────────────────────────────────────────────────────────────────┤
  │ Sector/Industry Dashboards │ Aggregate insights across an industry                               │
  ├────────────────────────────┼─────────────────────────────────────────────────────────────────────┤
  │ Earnings Call Transcripts  │ Extend beyond SEC filings to earnings calls                         │
  ├────────────────────────────┼─────────────────────────────────────────────────────────────────────┤
  │ Sentiment Scoring          │ Quantified sentiment trends over time                               │
  └────────────────────────────┴─────────────────────────────────────────────────────────────────────┘
  Tier 4: Infrastructure
  ┌────────────────────────────────┬────────────────────────────────────────────┐
  │            Feature             │                    Why                     │
  ├────────────────────────────────┼────────────────────────────────────────────┤
  │ Alembic migrations             │ Required before any schema changes         │
  ├────────────────────────────────┼────────────────────────────────────────────┤
  │ Redis caching                  │ Performance for repeated queries           │
  ├────────────────────────────────┼────────────────────────────────────────────┤
  │ API rate limiting & versioning │ Production hardening                       │
  ├────────────────────────────────┼────────────────────────────────────────────┤
  │ E2E test suite                 │ Confidence for rapid iteration             │
  ├────────────────────────────────┼────────────────────────────────────────────┤
  │ Background job queue           │ For async ingestion and content generation │
  └────────────────────────────────┴────────────────────────────────────────────┘