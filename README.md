# Symbology

![Symbology Logo](https://i.imgur.com/SHcZkb2.png)

A full-stack application for retrieving, processing, analyzing, and visualizing financial data from SEC EDGAR filings.

## Overview

Symbology is a financial data processing and analysis system designed to extract structured information from public company filings. It connects to the SEC EDGAR database, retrieves financial statements and other key information, processes the data, and presents it through an intuitive web interface.

The system architecture consists of:
- **Data Ingestion Layer**: Connects to SEC EDGAR to fetch and process filing data
- **Database Layer**: Stores structured financial and textual data in PostgreSQL
- **API Layer**: Provides endpoints for accessing the processed data
- **UI Layer**: Svelte-based frontend for visualizing and interacting with financial data
- **LLM Integration**: Connects to OpenAI API for advanced financial document analysis

The system is particularly focused on 10-K annual reports and extracts:
- Company information
- Balance sheets
- Income statements
- Cash flow statements
- Cover page information
- Business descriptions
- Risk factors
- Management discussions and analysis

## Features

- **SEC EDGAR Integration**: Connect to the SEC's EDGAR system to retrieve company filings
- **XBRL Processing**: Parse and process XBRL financial data from filings
- **Data Storage**: Store structured financial data in a PostgreSQL database
- **Financial Analysis**: Access financial statements across multiple reporting periods
- **Textual Analysis**: Extract and store narrative sections of financial reports
- **Interactive UI**: Svelte-based user interface for browsing companies, filings, and documents
- **LLM Integration**: Leverage AI models for enhanced document analysis and insights
- **API Layer**: RESTful API for accessing company, filing, and document data
- **CLI Interface**: Command-line tools for data retrieval and processing

## Current Status

As we approach the v0.1.0 release, the project now includes:
- Stable data ingestion pipeline for SEC EDGAR filings
- Comprehensive database schema for financial and textual data
- RESTful API with endpoints for accessing companies, filings, and documents
- Basic Svelte UI with components for company, filing, and document selection
- Document viewer for financial report visualization
- Partial integration with LLM services for advanced text analysis

## Installation

### Prerequisites

- Python 3.13+
- PostgreSQL database
- Node.js and npm (for UI development)
- Docker (for running services in containers)

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/symbology.git
   cd symbology
   ```

2. **Set up environment variables**
   Create a `.env` file in the project root:
   ```
   # Database settings
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=postgres
   POSTGRES_DB=symbology
   DATABASE_HOST=localhost
   DATABASE_PORT=5432

   # API settings
   SYMBOLOGY_API_HOST=localhost
   SYMBOLOGY_API_PORT=8000
   EDGAR_CONTACT=your-email@example.com

   # UI settings
   SYMBOLOGY_UI_HOST=localhost
   SYMBOLOGY_UI_PORT=5173

   # LLM settings
   OPENAI_HOST=localhost
   OPENAI_PORT=11434
   ```

3. **Install backend dependencies using UV**
   ```bash
   uv pip install -r requirements.lock
   ```

4. **Install frontend dependencies**
   ```bash
   cd ui
   npm install
   cd ..
   ```

5. **Start the services**
   ```bash
   just start-db      # Start PostgreSQL database
   just start-api     # Start the API server
   just start-ui      # Start the UI development server
   ```

## Usage

### Using the UI

Once all services are running, access the UI at `http://localhost:5173` to:
- Browse available companies
- Select company filings
- View financial documents and statements
- Analyze financial data

### Processing 10-K Filings via CLI

Process 10-K filings for multiple companies and years:

```bash
just run 10k --tickers AAPL MSFT GOOGL --years 2022 2023
```

## Architecture

The system follows a layered architecture:

1. **Data Ingestion Layer** (`src/ingestion`)
   - Connects to SEC EDGAR
   - Processes XBRL and textual data
   - Feeds processed data to the database

2. **Database Layer** (`src/database`)
   - PostgreSQL database with SQLAlchemy ORM
   - Stores company information, filings, financial data, and document text

3. **API Layer** (`src/api`)
   - FastAPI-based REST API
   - Endpoints for companies, filings, documents, and financial data

4. **UI Layer** (`ui/`)
   - Svelte-based frontend
   - Components for data selection and visualization
   - Responsive design for desktop and mobile viewing

5. **LLM Integration** (`src/llm`)
   - Connects to OpenAI API
   - Provides advanced document analysis
   - Stores prompts, completions, and ratings

## Database Schema

The database consists of several interconnected tables:

- `companies`: Basic company information
- `filings`: Filing metadata for each document
- `financial_concepts`: Standardized financial concepts from XBRL taxonomies
- Financial statements:
  - `balance_sheet_values`
  - `income_statement_values`
  - `cash_flow_statement_values`
  - `cover_page_values`
- Textual information:
  - `business_descriptions`
  - `risk_factors`
  - `management_discussions`
- LLM-related:
  - `prompts`
  - `completions`
  - `ratings`

## Development

### Running Tests

```bash
just test
```

### Code Style

The project uses Ruff for linting and code formatting:

```bash
just lint
```

### Upcoming Features

See [ROADMAP.md](ROADMAP.md) for details on upcoming features and development plans.

## License

[Specify your license here]

## Acknowledgments

- SEC EDGAR database
- Edgar Tools Python library
- SQLAlchemy
- PostgreSQL
- Svelte
- FastAPI
- OpenAI