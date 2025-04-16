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

## Future

### Prompt Engineering / Inference Workflow
- [ ] Develop interface for configuring query parameters
- [ ] Create selector for source documents (by ticker/year → form type → section)
- [ ] Implement source retrieval from DB with fallback to process_10k
- [ ] Design UI for presenting generated text for review
- [ ] Add functionality for capturing user ratings and comments
- [ ] Store generated text in DB alongside prompt and query metadata
