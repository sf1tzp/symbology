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

## Next (v0.1.0)

The main release objectives of v0.1.0 are to
- bootstrap a svelete UI
- create basic components:
  - Company Selector
  - Filings Selector
  - Document Selector
  - Document Viewer
- Integrate those components with their associated API routes
- Include linting and testing

We should also review the various program configurations:
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
- Database IDs should use uuid v7

## Future

### UI Tweaks
- Reactive / Collapseable Cards
- Prepare side by side layout for Prompt Engineering:

### Prompt Engineering / Inference Workflow
- [ ] Develop interface for configuring query parameters
- [ ] Create selector for source documents (by ticker/year → form type → section)
- [ ] Implement source retrieval from DB with fallback to process_10k
- [ ] Design UI for presenting generated text for review
- [ ] Add functionality for capturing user ratings and comments
- [ ] Store generated text in DB alongside prompt and query metadata


## Public Release

- Must disclaim this is not financial advice
- Must add license

- Fundamental Ratios


## Stretch

# Detailed stock price charting / trend analysis

# Search recent news
# - avg topics of n most recent headlines about x
#   - compare long term headlines with recent for trending signals
#
