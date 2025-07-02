# Symbology

![Symbology Logo](https://i.imgur.com/v0cp4d1.png)

A financial intelligence platform that transforms SEC EDGAR filings into AI-powered insights through automated document processing and analysis.

## Overview

Symbology is an AI-driven financial analysis system that automatically processes SEC filings and generates intelligent summaries and insights. The platform retrieves documents from the SEC EDGAR database, processes them with large language models, and presents the results through a streamlined web interface optimized for financial research and analysis.

**Key Capabilities:**
- **Automated Document Processing**: Ingests 10-K filings and extracts key sections (Management Discussion & Analysis, Risk Factors, Business Description)
- **AI-Powered Analysis**: Uses LLMs to generate comprehensive summaries and insights from financial documents
- **Intelligent Aggregation**: Combines multiple document analyses into cohesive company-level insights
- **Research-Focused UI**: Clean, focused interface for navigating from companies to detailed document analysis

## Architecture

The system follows a streamlined data flow designed for AI-enhanced financial research:

```
SEC EDGAR → Document Ingestion → LLM Processing → Aggregated Insights → Research UI
```

### Core Components

1. **Document Ingestion** (`src/ingestion/`)
   - Connects to SEC EDGAR database
   - Extracts structured and textual data from 10-K filings
   - Stores documents in PostgreSQL for processing

2. **AI Processing Pipeline** (`src/llm/`)
   - Processes documents with configurable LLM models
   - Generates completions for specific document sections
   - Creates aggregated insights across multiple filings

3. **Database Layer** (`src/database/`)
   - PostgreSQL with SQLAlchemy ORM
   - Optimized schema for companies, documents, completions, and aggregates
   - Relationship tracking between companies, filings, and AI-generated content

4. **API Layer** (`src/api/`)
   - FastAPI-based REST API
   - Simplified endpoints aligned with research workflow
   - Focus on companies → aggregates → completions → documents flow

5. **Research Interface** (`ui/`)
   - Svelte-based frontend
   - Streamlined navigation: Company List → Company Detail → Aggregate Overview → Completion Overview → Document Overview
   - Optimized for financial research and analysis workflows

## Current Features

### Data Processing
- **SEC Filing Ingestion**: Automated retrieval and processing of 10-K annual reports
- **Document Extraction**: Intelligent extraction of Management Discussion & Analysis, Risk Factors, and Business Descriptions
- **XBRL Processing**: Parse financial data from structured XBRL filings
- **Multi-Company Processing**: Batch processing across multiple companies and years

### AI Analysis
- **Document Completions**: LLM-generated analysis of individual document sections
- **Intelligent Aggregation**: Combines insights across multiple documents into company-level summaries
- **Configurable Models**: Support for various LLM models with customizable parameters
- **Quality Tracking**: Rating system for AI-generated content

### Research Interface
- **Company Discovery**: Search and browse companies with SEC filings
- **Aggregate Insights**: View AI-generated summaries by document type (MDA, Risk Factors, Business Description)
- **Source Traceability**: Navigate from aggregates to source completions to original documents
- **Document Viewer**: Full-text viewing of original SEC documents

## Installation

### Prerequisites

- Python 3.13+
- PostgreSQL database
- Node.js 18+ (for UI development)
- Docker (optional, for containerized services)
- Access to LLM service (OpenAI API or local model via Ollama)

### Quick Start

1. **Clone and Setup**
   ```bash
   git clone https://github.com/yourusername/symbology.git
   cd symbology

   # Install Python dependencies
   uv venv && source .venv/bin/activate
   uv pip install -r requirements.lock

   # Install UI dependencies
   cd ui && npm install && cd ..
   ```

2. **Configure Environment**
   Create `.env` file:
   ```env
   # SEC EDGAR
   EDGAR_CONTACT=your-email@example.com

   # Database
   DATABASE_HOST=localhost
   DATABASE_PORT=5432
   DATABASE_USER=postgres
   DATABASE_PASSWORD=your-password
   DATABASE_NAME=symbology

   PGADMIN_EMAIL=admin@example.com
   PGADMIN_PASSWORD=admin-password

   # LLM Service
   OPENAI_API_HOST=localhost
   OPENAI_API_PORT=11434

   # API & UI
   SYMBOLOGY_API_HOST=localhost
   SYMBOLOGY_API_PORT=8000
   SYMBOLOGY_UI_HOST=localhost
   SYMBOLOGY_UI_PORT=5173

   # Logging
   LOG_LEVEL=INFO
   ```

3. **Start Services**
   ```bash
   just run db      # Start PostgreSQL
   just run api     # Start API server (localhost:8000)
   just run ui      # Start UI dev server (localhost:5173)
   ```

## Usage

### Processing Company Filings

Process 10-K filings and generate AI analysis:

```bash
# Process single company
just run 10k --tickers AAPL --years 2023

# Process multiple companies
just run 10k --tickers AAPL MSFT GOOGL --years 2022 2023

# Generate AI completions for processed documents
python -m src.llm.completions --ticker AAPL --model gpt-4

# Create aggregated insights
python -m src.llm.aggregations --ticker AAPL --model gpt-4
```

### Research Workflow

1. **Company Discovery**: Browse companies at `http://localhost:5173`
2. **Aggregate Insights**: View AI-generated summaries by document type
3. **Source Analysis**: Drill down to individual completions that created the aggregates
4. **Document Review**: Access original SEC filing text

### API Access

The API provides programmatic access to all data:

```bash
# Search companies
curl "http://localhost:8000/api/companies/search?query=apple&limit=10"

# Get company aggregates
curl "http://localhost:8000/api/aggregates/by-ticker/AAPL"

# Get completion details
curl "http://localhost:8000/api/completions/{completion-id}"

# Get document content
curl "http://localhost:8000/api/documents/{document-id}/content"
```

## Database Schema

The database is optimized for AI-enhanced financial research:

**Core Entities:**
- `companies`: Company master data (name, ticker, CIK)
- `filings`: SEC filing metadata and relationships
- `documents`: Extracted document sections (MDA, Risk Factors, etc.)

**AI-Generated Content:**
- `completions`: LLM-generated analysis of individual documents
- `aggregates`: Higher-level insights combining multiple completions
- `prompts`: Reusable prompt templates for consistent analysis

**Relationships:**
- Companies → Filings → Documents (source content)
- Documents → Completions → Aggregates (AI processing pipeline)
- Full traceability from aggregates back to source documents

## Development

### Testing
```bash
just test py     # Run Python tests
just test ui     # Run UI tests
just test        # Run all tests
```

### Code Quality
```bash
just lint py     # Lint Python code
just lint ui     # Lint UI code
just format      # Format all code
```

### Adding New Models

The system supports pluggable LLM models. See `src/llm/models.py` for configuration options.

## Current Status

**Version 0.2.0** - AI-Enhanced Research Platform

✅ **Complete:**
- SEC EDGAR document ingestion pipeline
- LLM processing for document analysis
- Aggregation system for multi-document insights
- Streamlined research UI (Company → Aggregate → Completion → Document)
- Comprehensive API with test coverage
- Database optimized for AI workflows

🚧 **In Progress:**
- Enhanced UI components for financial data visualization
- Advanced rating and quality assessment system
- Expanded LLM model support

📋 **Planned:**
- Financial data analysis and visualization
- Advanced search and filtering capabilities
- Export and reporting features
- Multi-user collaboration tools

See [ROADMAP.md](ROADMAP.md) for detailed development plans.

## Contributing

Symbology is designed for financial researchers, data scientists, and developers working with SEC filings. Contributions are welcome in:

- Document processing improvements
- AI model integrations
- UI/UX enhancements
- Financial analysis features

## License

[Specify your license here]

## Acknowledgments

- **SEC EDGAR**: Primary data source for financial filings
- **Edgar Tools**: Python library for SEC data access
- **OpenAI/Ollama**: LLM processing capabilities
- **FastAPI & Svelte**: Modern web framework stack
- **PostgreSQL**: Robust data storage and relationships