# Symbology Roadmap

This document outlines the future development path for the Symbology project after the 0.1 release.

## Current Status (v0.1.0)

The initial 0.1.0 release includes:
- Basic SEC EDGAR integration for retrieving company information and 10-K filings
- XBRL processing for major financial statements (balance sheet, income statement, cash flow)
- PostgreSQL database storage with comprehensive data models
- CLI interface for data retrieval and processing
- Comprehensive test suite with database and ingestion tests

## Upcoming (v0.2.0)

The next release will focus on AI inference and prompt engineering capabilities:

### AI Integration
- [x] Implement fully customizable prompts
- [x] Support configurable query parameters (temperature, top_k, etc.)
- [x] Create pipeline to pull source data from database, make requests to OpenAI endpoint, and store results
- [x] Implement storage for query metadata including user ratings and comments on generated text

### REST API

This python program should listen on a configurable HOST and PORT
- routes should be facilitated to exercise the CRUD workflows

### Prompt Engineering / Inference Workflow
- [ ] Develop interface for configuring query parameters
- [ ] Create selector for source documents (by ticker/year → form type → section)
- [ ] Implement source retrieval from DB with fallback to process_10k
- [ ] Design UI for presenting generated text for review
- [ ] Add functionality for capturing user ratings and comments
- [ ] Store generated text in DB alongside prompt and query metadata

### Documentation
- [ ] Create comprehensive `INFERENCE_STRATEGY.md` document that will explain:
  - Types of summaries and narratives we aim to generate
    - Company risk response analysis over time
    - Management competency assessment (judgment & commitment)
    - Company financial position evaluation
    - Additional strategic analyses
  - Documentation of query parameters and prompt strategies
  - Methods for comparing source documents over time

## Future (v1.0.0)

The first major release will feature a comprehensive web UI for the project:

### Web Interface
- [ ] Develop intuitive UI for prompt engineering
- [ ] Create interface for reviewing and evaluating generated text
- [ ] Implement user authentication and session management
- [ ] Design responsive layouts for desktop and mobile access

### Company Data Visualization
- [ ] Build company profile pages displaying:
  - Ticker and basic information
  - Key financial metrics with visualizations
  - Performance summaries with trend analysis
  - Document navigation and section highlights
  - AI-generated insights and analysis

