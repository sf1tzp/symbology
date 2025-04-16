# Symbology Project Organization

This document outlines the organizational structure and design principles of the Symbology project.

## Project Architecture

Symbology follows a modular architecture with clear separation of concerns:

```
src/
├── api/             # REST API interface (FastAPI)
├── bin/             # CLI tools and scripts
├── database/        # Database models and access layers
├── ingestion/       # Data processing pipeline
│   └── edgar_db/    # SEC EDGAR specific code
├── llm/             # LLM integration and prompt engineering
├── utils/           # Shared utilities
└── tests/           # Test suite organized by module
```

## Design Principles

1. **Separation of Concerns**: Each module has a single, well-defined responsibility
   - `api`: Exposes functionality to external clients
   - `database`: Manages data models and storage
   - `ingestion`: Processes financial data
   - `llm`: Handles AI model integration
   - `bin`: Provides command-line interfaces

2. **Dependency Direction**: Dependencies flow from interface layers to core functionality
   - The API module depends on database and ingestion capabilities
   - Core modules operate independently of interface concerns

3. **Modularity**: Components are designed to be loosely coupled
   - Database models are isolated from business logic
   - LLM functionality is separate from data processing

## Module Responsibilities

### API (src/api/)

The API module serves as the front door for interacting with the Symbology system:
- RESTful endpoints for data access and operations
- Authentication and authorization
- Request validation and error handling
- Routing to appropriate business logic

### Database (src/database/)

The database module handles data modeling and storage:
- Database schema definitions
- ORM models for various entity types
- Query interfaces and data access patterns

### Ingestion (src/ingestion/)

The ingestion module handles data processing:
- SEC EDGAR data retrieval and parsing
- XBRL financial statement processing
- Integration with database storage

### LLM (src/llm/)

The LLM module manages AI integration:
- Client interfaces to language models
- Prompt engineering and management
- Text processing and analysis utilities

### CLI Tools (src/bin/)

The bin module provides command-line utilities:
- Data ingestion scripts
- Maintenance and administration tools
- Batch processing capabilities

## Testing Strategy

Tests are organized to mirror the project structure:
- Unit tests focus on individual components
- Integration tests verify module interactions
- Database tests ensure proper data modeling and storage

## Future Extensions

The project is designed to easily accommodate:
- Additional data sources beyond SEC EDGAR
- New financial analysis capabilities
- Enhanced visualization and reporting tools
- Expanded API functionality