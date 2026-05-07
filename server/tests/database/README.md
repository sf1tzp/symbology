# Database Testing Documentation

This directory contains comprehensive tests for the Symbology database models, relationships, and CRUD operations.

## Test Structure

Tests are organized by model, with each model having a dedicated test file:

- `test_companies.py`: Tests for the Company model
- `test_filings.py`: Tests for the Filing model
- `test_documents.py`: Tests for the Document model
- `test_financial_concepts.py`: Tests for the FinancialConcept model
- `test_financial_values.py`: Tests for the FinancialValue model
- `test_completions.py`: Tests for the Completion model
- `test_ratings.py`: Tests for the Rating model
- `test_prompts.py`: Tests for the Prompt model

## Test Fixtures

Common fixtures are provided for all tests:

- Database session fixtures: `db_engine`, `db_session`
- Sample entity data fixtures for each model
- Relationship fixtures establishing connections between models

## Model CRUD Operation Tests

For each model, the following CRUD operations are tested:

### Company Model (`test_companies.py`)
- **Creation**: Basic creation, minimal data creation, creation with former names
- **Retrieval**: By ID, using string UUIDs
- **Updates**: Field updates, handling invalid attributes
- **Deletion**: Basic deletion, verification of cascading deletes
- **Constraints**: Duplicate CIK, duplicate EIN handling
- **Function Coverage**: `create_company`, `get_company`, `update_company`, `delete_company`, `get_company_ids`

### Filing Model (`test_filings.py`)
- **Creation**: Basic creation, minimal data creation
- **Retrieval**: By ID, using string UUIDs
- **Updates**: Field updates, handling invalid attributes
- **Deletion**: Basic deletion, verification of cascading deletes
- **Relationships**: Filing-Company relationship
- **Function Coverage**: `create_filing`, `get_filing`, `update_filing`, `delete_filing`, `get_filing_ids`

### Document Model (`test_documents.py`)
- **Creation**: Basic creation, minimal creation, creation without filing
- **Retrieval**: By ID, using string UUIDs
- **Updates**: Field updates, handling invalid attributes
- **Deletion**: Basic deletion, verification of cascading deletes
- **Relationships**: Document-Company and Document-Filing relationships
- **Function Coverage**: `create_document`, `get_document`, `update_document`, `delete_document`, `get_document_ids`
- **Cascade Tests**: Deleting parent Company or Filing cascades to Documents

### Financial Concept Model (`test_financial_concepts.py`)
- **Creation**: Basic creation
- **Retrieval**: By ID, using string UUIDs
- **Updates**: Field updates, handling invalid attributes
- **Deletion**: Basic deletion, verification of cascading deletes
- **Relationships**: FinancialConcept-FinancialValue relationship
- **Function Coverage**: `create_financial_concept`, `get_financial_concept`, `update_financial_concept`, `delete_financial_concept`, `get_financial_concept_ids`

### Financial Value Model (`test_financial_values.py`)
- **Creation**: Basic creation, creation without filing
- **Retrieval**: By ID, using string UUIDs
- **Updates**: Field updates, handling invalid attributes
- **Deletion**: Basic deletion
- **Relationships**: With Company, FinancialConcept, and Filing
- **Function Coverage**: `create_financial_value`, `get_financial_value`, `update_financial_value`, `delete_financial_value`, `get_financial_value_ids`
- **Cascade Tests**: Deleting parent Company, FinancialConcept, or Filing cascades to FinancialValues

### Completion Model (`test_completions.py`)
- **Creation**: Basic creation, minimal creation
- **Retrieval**: By ID, using string UUIDs
- **Updates**: Field updates, updating document associations, handling invalid attributes
- **Deletion**: Basic deletion
- **Relationships**: With Documents and Prompts
- **Function Coverage**: `create_completion`, `get_completion`, `update_completion`, `delete_completion`, `get_completion_ids`
- **JSON Operations**: Testing JSON field operations for context_text

### Rating Model (`test_ratings.py`)
- **Creation**: Basic creation, minimal creation
- **Retrieval**: By ID, using string UUIDs
- **Updates**: Field updates, handling invalid attributes
- **Deletion**: Basic deletion
- **Relationships**: Rating-Completion relationship
- **Function Coverage**: `create_rating`, `get_rating`, `update_rating`, `delete_rating`, `get_rating_ids`
- **Validation**: Content score and format score range validation (1-10)
- **Cascade Tests**: Deleting parent Completion cascades to Ratings

### Prompt Model (`test_prompts.py`)
- **Creation**: Basic creation for system, user, and assistant roles
- **Retrieval**: By ID, using string UUIDs
- **Updates**: Field updates, updating prompt role, handling invalid attributes
- **Deletion**: Basic deletion
- **Relationships**: With Completions as system or user prompts
- **Function Coverage**: `create_prompt`, `get_prompt`, `update_prompt`, `delete_prompt`, `get_prompt_ids`
- **Constraints**: Testing duplicate name handling

## Relationship Testing

Special tests focus on the relationships between models:

- Company -> Filings, Documents, FinancialValues
- Filing -> Documents, FinancialValues
- Document <-> Completion (many-to-many)
- FinancialConcept -> FinancialValues
- Completion -> Ratings
- Prompt -> Completions (as system_prompt or user_prompt)

### Cascade Delete Tests

Tests verify that deleting parent entities properly handles child entities:

- Deleting a Company deletes associated Filings, Documents, and FinancialValues
- Deleting a Filing deletes associated Documents and FinancialValues
- Deleting a FinancialConcept deletes associated FinancialValues
- Deleting a Completion deletes associated Ratings
- Deleting a Prompt does NOT delete associated Completions
- Deleting a Document does NOT delete associated Completions
