# Symbology

A Python application for retrieving, processing, and analyzing financial data from SEC EDGAR filings.

## Overview

Symbology is a financial data processing system designed to extract structured information from public company filings. It connects to the SEC EDGAR database, retrieves financial statements and other key information, processes the data, and stores it in a PostgreSQL database for further analysis.

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
- **CLI Interface**: Command-line tools for data retrieval and processing

## Installation

### Prerequisites

- Python 3.13+
- PostgreSQL database
- Docker (for running the database in a container)

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
   DATABASE_URL=postgresql://postgres:postgres@localhost:5432/symbology
   
   # API settings
   EDGAR_CONTACT=your-email@example.com
   ```

3. **Install dependencies using UV**
   ```bash
   uv pip install -r requirements.lock
   ```

4. **Start the database**
   ```bash
   just start-db
   ```

## Usage

### Demo

Run a simple demo that fetches and stores information for Microsoft:

```bash
just run demo
```

### Process 10-K Filings

Process 10-K filings for multiple companies and years:

```bash
just run 10k --tickers AAPL MSFT GOOGL --years 2022 2023
```

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

## License

[Specify your license here]

## Acknowledgments

- SEC EDGAR database
- Edgar Tools Python library
- SQLAlchemy
- PostgreSQL