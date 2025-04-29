# Symbology Roadmap

This document outlines the future development path for the Symbology project after the 0.1 release.

## (v0.0.1)

The v0.0.1 release included:
- Basic SEC EDGAR integration for retrieving company information and 10-K filings
- XBRL processing for major financial statements (balance sheet, income statement, cash flow)
- PostgreSQL database storage with comprehensive data models
- CLI interface for data retrieval and processing
- Comprehensive test suite with database and ingestion tests

## (v0.0.2)

The v0.0.2 release included:
- Flattening of the project `src/` directory
- Refactoring `src/database` with a focus on consistent implementation
- Addition of `src/api` with endpoints to support basic UI components
- Adaptation of `src/tests` to cover the new database and API functions

## (v0.1.0)

The v0.1.0 release includes:
- [x] bootstrap a svelete UI
    - create basic components:
      - Company Selector
      - Filings Selector
      - Document Selector
      - Document Viewer
    - Integrate those components with their associated API routes
    - Include linting and testing

- [x] We should also review the various program configurations:
  - src/ingestion/config.py seems the most robust
    - Probably move this to src/utils
    - need to ensure sections for each endpoint, at the minimum:
      - OPEN_AI_API_HOST / PORT (default localhost:11434)
      - DATABASE_HOST / PORT (default localhost:5432)
      - PGADMIN_HOST / PORT (default localhost:8080)
      - SYMBOLOGY_API_HOST / PORT (default localhost:8000)
      - SYMBOLOGY_UI_HOST / PORT (default localhost:5173)
  - src/api/main can use src/utils/config.py
  - Update justfile recipes to use correct env var passing

- [x] Database IDs should use uuid v7

## Next (v0.1.1)



### Enhance API Functionality
- [x] Automatically ingest company if not found (get past 5 10-Ks)
- [ ] Auto-populate search suggestions for 'not ingested' tickers

### UI Tweaks
- [x] Search Bar Enhancements
  - Auto Populate Company Search bar with results
  - Filter list down as typing

- [x] Reactive / Collapseable Cards
  - for example, CompanySelector:
    - Currently, when a company is selected, we show a `company-details` div
    - Ideally, when a company is selected we should hide the search bar and heading
    - After a company is selected, when the user hovers / focuses the `company-selector` we should show the search bar and heading again

- [ ] Prepare side by side layout :
  - When Company, Filing, and Document are selected (And DocumentViewer content is loaded)
  - Let's shift the UI into a horizontal layout:
    - Along the top row we should show our three selector components
    - In the second row, we should have two cards:
      - First, the DocumentViewer component
      - Second, a similarly styled placeholder component

### Prompt Engineering / Inference Workflow
- [ ] Add routes to support Prompt Engineering UI
  - Prompts
    - get prompts by role
    - create prompt

  - Generate Completion


  - Get Completions (by document id)
- [ ] Add components for Prompt Engineering UI [canvas](ui/llm-layouts.canvas)

## Future Enhancements (v0.2.0)

### WebSocket Integration
- [ ] Implement real-time ingestion updates with WebSockets
  - Add WebSocket server to FastAPI backend
  - Add WebSocket client to Svelte frontend
  - Refactor ingestion process to provide real-time status updates
  - Add progress indicators for ingestion process
  - See detailed plan in [migrate-to-websockets.md](migrate-to-websockets.md)

- When ingesting data, show filings, update the list of shown filings as they are ingested
- ingest data in parallel


## Public Release TODOs

- Must disclaim this is not financial advice
- Must add license

- Display Fundamental Ratios

- 'Like what you see, but can't find what you're looking for? Support the project and request coverage on patreon'

## Stretch

# Detailed stock price charting / trend analysis

# Search recent news
# - avg topics of n most recent headlines about x
#   - compare long term headlines with recent for trending signals
#
