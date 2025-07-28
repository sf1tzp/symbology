# Symbology

![Symbology Logo](https://i.imgur.com/v0cp4d1.png)


Explore LLM-generated insights on publicly traded companies. Symbology leverages company filings to identify trends and developments since the COVID-19 pandemic.

[symbology.online](https://symbology.online)

## Overview

Symbology transforms SEC EDGAR filings into AI-powered insights through automated document processing and analysis. The platform captures the full scope of extensive company filings by using language models with large context windows to ingest source material, then employs 'thinking' models to compare reports across years, highlighting changes and emerging trends over time.

Each report's generation process – including model, prompt engineering, and context – is fully documented, allowing analysis to be traced back to original SEC filings for reproducible results.

## Architecture

The system follows a streamlined data flow designed for AI-enhanced financial research:

```
SEC EDGAR → Document Ingestion → LLM Processing → Aggregated Insights → Research UI
```

### Core Components

- **Document Ingestion**: Automated retrieval and processing of SEC filings with intelligent extraction of key sections
- **AI Processing Pipeline**: LLM-powered analysis generating summaries and insights from financial documents
- **Database Layer**: PostgreSQL schema optimized for companies, documents, completions, and aggregated insights
- **API Layer**: FastAPI-based REST interface aligned with research workflows
- **Research Interface**: Svelte-based frontend for navigating companies, aggregates, completions, and source documents

## Technology Stack

- **Backend**: Python with FastAPI, PostgreSQL, SQLAlchemy ORM
- **Frontend**: Svelte 5 with TypeScript
- **AI Integration**: Compatible with OpenAI API and local models via Ollama
- **Infrastructure**: Docker support with configurable deployment options

## Data Flow

The platform processes SEC EDGAR filings through a multi-stage pipeline:

1. **Ingestion**: Automated retrieval and parsing of 10-K annual reports
2. **Extraction**: Intelligent extraction of key sections (Management Discussion & Analysis, Risk Factors, Business Description)
3. **Analysis**: LLM processing to generate summaries and insights
4. **Aggregation**: Combination of insights across multiple documents and time periods
5. **Research Interface**: Streamlined navigation from companies to source documents

## Database Schema

Core entities optimized for AI-enhanced financial research:
- **Companies & Filings**: Company master data and SEC filing metadata
- **Documents**: Extracted document sections with full text content
- **Completions**: LLM-generated analysis of individual documents
- **Aggregates**: Higher-level insights combining multiple completions
- **Prompts**: Reusable templates for consistent analysis

Full traceability maintained from aggregates back to source documents.

## Current Status

**Version 0.0.1** - Initial release

This is an open-source project designed for financial researchers, data scientists, and developers working with SEC filings. All content and analysis processes are fully documented and reproducible.

See the [project repository](https://github.com/sf1tzp/symbology) for source code and detailed documentation.