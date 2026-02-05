# Symbology

![Symbology Logo](https://i.imgur.com/v0cp4d1.png)

Explore LLM-generated insights on publicly traded companies. Symbology leverages company filings to identify trends and developments since the COVID-19 pandemic.

[symbology.online](https://symbology.online)

## Acknowledgements

- [trade bots](https://store.steampowered.com/app/1899350/Trade_Bots_A_Technical_Analysis_Simulation/)
- [investopedia](https://www.investopedia.com/)
- [edgartools](https://github.com/dgunning/edgartools)



----

● Symbology Codebase Review

  What it is: An LLM-powered financial research platform that ingests SEC EDGAR filings (10-K, 10-Q) and generates AI-synthesized insights — think automated equity research analyst.
  Live at symbology.online.

  Tech Stack Summary

  - Backend: Python 3.13, FastAPI, SQLAlchemy 2.0, PostgreSQL
  - Frontend: SvelteKit, TypeScript, Tailwind CSS, Bits UI
  - LLM: Ollama (local inference)
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
  8. LLM tightly coupled to Ollama — no support for cloud LLM APIs
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
  │ Cloud LLM Support          │ Move beyond local Ollama to Claude/GPT for higher quality and scale │
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