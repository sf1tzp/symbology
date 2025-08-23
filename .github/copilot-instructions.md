# Symbology AI Coding Guidelines


## Project Overview
Symbology is a financial intelligence platform that transforms SEC EDGAR filings into AI-powered insights. The system processes 10-K reports through a multi-stage pipeline: ingestion → LLM processing → aggregated insights → research UI.

## Environment & Tools
- **Python Environment**: Uses `uv` for dependency management with `.venv` at project root
- **Build System**: `just` commands for all operations - never use `python` directly, always prefix with `uv run`
- **Development Servers**: API and UI auto-reload on changes, run in separate terminals
- **Database**: PostgreSQL with Alembic migrations managed via `just` commands

## Key Commands & Workflows

### Essential Just Commands
```bash
# Component operations (api, ui, db, ingest, generate)
just run api              # Start FastAPI server (uv run -m src.api.main)
just run ui               # Start Svelte dev server
just run ingest AAPL 2022 # Ingest SEC filings
just run generate AAPL 2022 # Generate LLM insights
just test api             # Run pytest with coverage
just lint api --fix      # Run ruff linting
```

### Database Management
```bash
# All database commands now available from root - NEVER run alembic directly
just db-upgrade          # Apply migrations
just db-auto-revision "description" # Auto-generate migration
just db-current          # Show current version
just db-history          # Show migration history
just db-reset            # Reset to base (destructive)
```

## Architecture Patterns

### Database Layer (`src/database/`)
- **Models**: SQLAlchemy with `Mapped` types, inherit from `Base`
- **CRUD Operations**: Separate modules per entity (companies.py, documents.py, etc.)
- **Key Relationships**: Companies → Filings → Documents → Completions → Aggregates
- **Content Hashing**: Use `get_short_hash()` method for content references

### API Layer (`src/api/`)
- **FastAPI Structure**: Routers in separate files, dependency injection pattern
- **Simplified Flow**: Company List → Company Detail → Aggregates → Completions → Documents
- **URL Pattern**: `/g/{ticker}/{content_hash}` for generated content links

### LLM Integration (`src/llm/`)
- **Client Abstraction**: OpenAI-compatible interface, supports Ollama local models
- **Prompt Engineering**: Template-based system with variable substitution
- **Content Processing**: Large context windows for full document ingestion

### Frontend (`ui/`)
- **Svelte 5**: With runes mode, TypeScript strict mode
- **API Types**: Auto-generated from backend via `just -d ui generate-api-types`
- **Navigation**: Streamlined research workflow with breadcrumb patterns

## Development Conventions

### Logging
- **Structured Logging**: Use `structlog` everywhere, `get_logger(__name__)`
- **Log to Files**: Test/lint outputs logged for LLM context inclusion
- **Console Format**: Clickable file paths in development, JSON in production

### Testing & Quality
- **Coverage**: Pytest with coverage for api, database, ingestion, llm modules
- **Linting**: Ruff with output logged to `lint.log`
- **Type Safety**: Full TypeScript strict mode, Python type hints throughout

### File Organization
- **Module Structure**: Clear separation - api/database/ingestion/llm/utils
- **Dependency Flow**: Interface layers (API) → core functionality (database)
- **Migration Scripts**: Database migration tools in `src/bin/`

## Integration Points

### SEC EDGAR Processing
- **edgartools**: Primary library for SEC filing retrieval and parsing
- **Document Extraction**: Focus on MDA, Risk Factors, Business Description sections
- **XBRL Processing**: Financial data extraction with concept mapping

### Model Configuration
- **Flexible Providers**: OpenAI API + Ollama local models
- **Model Configs**: Database-stored configurations with options (temperature, context length)
- **Content Hashing**: SHA256 hashing for content deduplication and traceability

### Environment Configuration
- **Settings Pattern**: Pydantic settings with environment variable mapping
- **Database URLs**: Environment-specific configuration via `.env`
- **API Integration**: Backend/frontend communication with CORS handling

When working with this codebase, always use `just` commands, understand the data flow from SEC filings to UI, and maintain the structured logging patterns throughout.
