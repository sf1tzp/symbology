# Symbology API

## Overview
The Symbology API provides RESTful endpoints for accessing financial data and AI-generated insights. Built with FastAPI, this API allows you to retrieve information about companies, filings, and associated documents.

## FastAPI Framework
This API is built using [FastAPI](https://fastapi.tiangolo.com/), a modern Python web framework for building APIs with Python 3.6+. FastAPI offers:

- **High Performance**: Comparable to NodeJS and Go, making it one of the fastest Python frameworks available
- **Automatic Documentation**: Interactive API documentation generated automatically via Swagger UI and ReDoc
- **Type Checking**: Based on Python type hints, providing automatic data validation
- **Modern Python**: Takes advantage of Python 3.6+ features and is based on standard Python type hints

## API Endpoints

### Health Check
- `GET /`: Check if API is online

### Companies
- `GET /api/companies/search`: Search for companies by partial name or ticker (autocomplete)
- `GET /api/companies/id/{company_id}`: Get a company by its UUID
- `GET /api/companies/?ticker={ticker}`: Get a company by ticker symbol
- `GET /api/companies/?cik={cik}`: Get a company by CIK

### Aggregates
- `GET /api/aggregates/by-ticker/{ticker}`: Get the most recent aggregates for each document type by company ticker
- `GET /api/aggregates/{aggregate_id}/completions`: Get all completions that were used as sources to create an aggregate

### Completions
- `GET /api/completions/{completion_id}`: Get a completion by its UUID

### Documents
- `GET /api/documents/{document_id}`: Get a document by its UUID
- `GET /api/documents/{document_id}/content`: Get a document's content by its UUID

## Simplified UI Flow

The API has been streamlined to support a simplified user interface flow:

1. **Company List** → Search companies (`/api/companies/search`)
2. **Company Detail** → Get company info (`/api/companies/id/{id}`) and aggregates (`/api/aggregates/by-ticker/{ticker}`)
3. **Aggregate Overview** → View aggregate data and get source completions (`/api/aggregates/{id}/completions`)
4. **Completion Overview** → Get completion details (`/api/completions/{id}`)
5. **Document Overview** → Get document info (`/api/documents/{id}`) and content (`/api/documents/{id}/content`)

The following endpoints have been removed as they are not part of the core user experience:
- Filing endpoints (users navigate through aggregates/completions instead)
- Prompt management endpoints (admin functionality)
- Most completion CRUD operations (users only view, not create/update/delete)

## Request and Response Schemas
The API uses Pydantic models for request validation:

- `CompanySearchRequest`: For company search by ticker or CIK
- `CompanyIdRequest`: For company lookup by UUID
- `FilingIdRequest`: For filing lookup by UUID
- `DocumentIdRequest`: For document lookup by UUID

## Example API Requests

For example API requests, refer to the `requests.http` file in this directory. This file contains a collection of HTTP requests that can be executed using REST client plugins available for various IDEs (such as VS Code's REST Client extension). The file includes sample requests for all available endpoints with placeholders for IDs that can be easily replaced with actual values.

## Configuration
The API server configuration can be customized through environment variables or configuration files. See the `src/api/config.py` file for details.

## Running the API
The API server can be started using:

```bash
just run --api
```

This will start the server with the configured host and port settings (defaults to localhost:8000).

## API Documentation
When the server is running, you can access the auto-generated API documentation:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### OpenAPI Documentation Features

The API uses FastAPI's built-in OpenAPI documentation capabilities with enhanced customization:

1. **Detailed Schema Documentation**: All request and response schemas are fully documented using Pydantic models with:
   - Field descriptions
   - Type annotations
   - Example values
   - Required vs. optional field indicators

2. **Customized Swagger UI**: The API uses a customized version of Swagger UI with:
   - Modern UI theme from the latest Swagger UI distribution
   - Organized endpoint grouping by tags (companies, filings, documents)
   - Interactive "Try it out" functionality to test API calls directly

3. **Response Documentation**: Each endpoint documents:
   - Success responses with example data
   - Possible error responses (404, 400, 500) with descriptions
   - Response content types

4. **API Metadata**: The documentation includes:
   - API version information
   - Contact information
   - License details
   - General API description

The documentation is automatically generated from the code annotations in the route handlers and Pydantic schemas, ensuring it always stays in sync with the actual implementation.
