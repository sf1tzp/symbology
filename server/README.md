# Symbology Backend Architecture

The Symbology backend follows a modular architecture with clear separation of concerns, designed for AI-enhanced financial research and analysis.

## Module Structure

```
server/
├── symbology/           # Python package
│   ├── api/             # REST API interface (FastAPI)
│   ├── cli/             # CLI tools (Click + Rich)
│   ├── database/        # Database models and access layers
│   ├── ingestion/       # Data processing pipeline
│   │   └── edgar_db/    # SEC EDGAR specific code
│   ├── llm/             # LLM integration and prompt engineering
│   ├── scheduler/       # Periodic EDGAR polling and pipeline triggering
│   ├── worker/          # Background job worker process
│   └── utils/           # Shared utilities
└── tests/               # Test suite organized by module
```

## Design Principles

**Separation of Concerns**: Each module serves a single, well-defined purpose with minimal dependencies between interface and core functionality.

**Dependency Direction**: Dependencies flow from interface layers (API) to core functionality (database, ingestion, LLM), allowing core modules to operate independently.

**Modularity**: Components are loosely coupled, enabling easy extension with new data sources, analysis capabilities, and API functionality.

## Module Responsibilities

- **API**: RESTful endpoints for data access, validation, and routing to business logic
- **Database**: Data modeling, schema definitions, and query interfaces for companies, filings, documents, completions, and aggregates
- **Ingestion**: SEC EDGAR data retrieval, parsing, and XBRL processing with database integration
- **LLM**: Language model integration, prompt engineering, and text analysis utilities
- **CLI Tools**: Command-line utilities for data ingestion, maintenance, and batch processing
- **Scheduler**: Periodic EDGAR polling process that detects new filings and enqueues pipeline jobs (see below)
- **Worker**: Background job queue processor using PostgreSQL `SELECT FOR UPDATE SKIP LOCKED` for atomic job claiming, with retry logic and stale detection

## Scheduler / Worker Pipeline

The scheduler and worker are separate long-lived processes that collaborate through the PostgreSQL job queue:

```
┌────────────┐       ┌──────────┐       ┌────────────┐
│  Scheduler │──────>│ Job Queue │──────>│   Worker   │
│            │ enqueue│ (postgres)│ claim  │            │
│ polls EDGAR│       │          │       │ runs        │
│ every 6hr  │       │          │       │ FULL_PIPELINE│
└────────────┘       └──────────┘       └─────┬──────┘
                                              │
                                        ┌─────▼──────┐
                                        │PipelineRun │
                                        │ (tracking) │
                                        └────────────┘
```

**Scheduler** (`just scheduler`) polls EDGAR on a configurable interval (default 6 hours). For each tracked company, it compares recent filing accession numbers against the database. When new filings are found, it enqueues a `FULL_PIPELINE` job with `trigger=scheduled`.

**Worker** (`just worker`) claims jobs from the queue and executes them. The `FULL_PIPELINE` handler orchestrates the full ingestion and content generation pipeline: company ingestion, filing ingestion, single/aggregate/frontpage summary generation.

**PipelineRun** tracks each end-to-end execution with status (PENDING/RUNNING/COMPLETED/FAILED/PARTIAL), job counters, and timing. This enables monitoring and alerting on pipeline health.

Configuration (environment variables):

| Variable | Default | Description |
|---|---|---|
| `SCHEDULER_POLL_INTERVAL` | `21600` | Seconds between polling cycles (6 hours) |
| `SCHEDULER_ENABLED_FORMS` | `["10-K", "10-Q"]` | SEC form types to watch |
| `SCHEDULER_FILING_LOOKBACK_DAYS` | `30` | How far back to check for new filings |
| `WORKER_POLL_INTERVAL` | `2.0` | Seconds between job queue polls |
| `WORKER_STALE_THRESHOLD` | `600` | Seconds before a running job is considered stale |

## Testing Strategy

Tests mirror the project structure with unit tests for individual components, integration tests for module interactions, and database tests for proper data modeling and storage.