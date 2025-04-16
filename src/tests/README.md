# Symbology Test Suite

This directory contains the comprehensive test suite for the Symbology project, a Python application for retrieving, processing, and analyzing financial data from SEC EDGAR filings.

## Overview

The test suite uses pytest as the testing framework and follows a structured approach to testing different components of the application:

- **Unit Tests**: Tests for individual functions and classes
- **Integration Tests**: Tests for database interactions and API endpoints
- **Functional Tests**: End-to-end tests for specific features

## Directory Structure

```
tests/
├── __init__.py        # Package initialization
├── conftest.py        # Global pytest configuration and fixtures
├── README.md          # This documentation
├── api/               # Tests for API endpoints
│   ├── test_*.py      # Tests for specific API routes
├── database/          # Tests for database models and operations
│   ├── fixtures.py    # Database-specific test fixtures
│   ├── test_*.py      # Tests for database models and operations
└── ingestion/         # Tests for data ingestion components
    └── test_*.py      # Tests for data ingestion functionality
```

## API Testing

The project includes tests for API endpoints using FastAPI's `TestClient`. These tests ensure that the API routes handle requests correctly, return appropriate responses, and properly integrate with the underlying database functions.

### API Test Structure

API tests are organized in the `src/tests/api/` directory with separate test files for different resource endpoints:

- `test_documents_api.py`: Tests for document retrieval endpoints
- `test_filings_api.py`: Tests for filing operations and related document retrieval
- `test_companies_api.py`: Tests for company search and retrieval endpoints

### Testing Approach

The API tests use mocking to isolate the API routes from actual database calls:

```python
@patch("src.api.routes.documents.get_document")
def test_get_document_by_id_found(self, mock_get_document):
    # Setup the mock to return sample data
    mock_get_document.return_value = SAMPLE_DOCUMENT_DATA

    # Make the API call using FastAPI's TestClient
    response = client.get(f"/api/documents/{SAMPLE_DOCUMENT_ID}")

    # Assert the response status code and data
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(SAMPLE_DOCUMENT_ID)

    # Verify the mock was called with the correct arguments
    mock_get_document.assert_called_once_with(SAMPLE_DOCUMENT_ID)
```

Each test class focuses on a specific API resource and includes tests for:

1. Successful requests with proper responses
2. Error cases (404 Not Found, 400 Bad Request)
3. Edge cases and validation errors

The API tests verify that:
- Routes handle valid requests correctly
- Routes return appropriate HTTP status codes
- Response bodies match expected formats
- Error handling is implemented properly
- Database functions are called with expected parameters

## Key Pytest Features Used

### Fixtures

Fixtures are a powerful feature of pytest that provide a way to set up and tear down test resources. The project uses fixtures extensively:

```python
@pytest.fixture
def sample_company_data():
    """Sample company data for testing."""
    return {
        "name": "Apple Inc.",
        "cik": "0000320193",
        # Additional fields...
    }
```

Access fixtures in tests by including them as parameters:

```python
def test_create_company(db_session, sample_company_data):
    # The fixture values are passed as parameters
    company = Company(**sample_company_data)
    # ...
```

### Database Testing

The `conftest.py` file sets up database testing infrastructure:

- `create_test_database`: Creates a test database for the test session
- `db_engine`: SQLAlchemy engine connected to the test database
- `db_session`: SQLAlchemy session for interacting with the test database

Database tests use these fixtures to run against an isolated test database:

```python
def test_create_company(db_session, sample_company_data):
    company = Company(**sample_company_data)
    db_session.add(company)
    db_session.commit()

    # Assertions...
```

### Test Parameterization

For testing multiple similar scenarios, we use pytest's parameterization:

```python
@pytest.mark.parametrize("input_data,expected_result", [
    ({"value1": 1, "value2": 2}, 3),
    ({"value1": -1, "value2": 1}, 0),
    # Additional test cases...
])
def test_function_with_multiple_inputs(input_data, expected_result):
    result = function_under_test(input_data["value1"], input_data["value2"])
    assert result == expected_result
```

### Mocking

We use mocking to isolate components during testing:

```python
def test_function_with_mocking(db_session, mocker):
    # Mock external dependencies
    mock_service = mocker.patch("src.module.external_service")
    mock_service.get_data.return_value = {"test": "data"}

    # Test the function that depends on external_service
    result = function_under_test()

    # Verify mock was called correctly
    mock_service.get_data.assert_called_once()
    # Additional assertions...
```

### Exception Testing

Testing for expected exceptions:

```python
def test_duplicate_cik(db_session, sample_company_data):
    # Create first company
    company1 = Company(**sample_company_data)
    db_session.add(company1)
    db_session.commit()

    # Try to create second company with same CIK
    company2 = Company(**sample_company_data)
    db_session.add(company2)

    # Should raise IntegrityError due to unique constraint
    with pytest.raises(IntegrityError):
        db_session.commit()
```

## Running Tests

To run the entire test suite:

```bash
just test
```

To run a specific test file:

```bash
pytest src/tests/database/test_companies.py -v
```

To run a specific test function:

```bash
pytest src/tests/database/test_companies.py::test_create_company -v
```

## Writing New Tests

When writing new tests, follow these guidelines:

1. **Use fixtures** for test setup and shared resources
2. **One assertion per test** when possible
3. **Descriptive test names** that explain what is being tested
4. **Isolate tests** so they don't depend on other tests
5. **Clean up resources** using fixture teardown

Example of a well-structured test:

```python
def test_get_company_by_ticker(db_session, sample_company_data):
    """Test retrieving a company by ticker symbol."""
    # Setup - create the test data
    company = Company(**sample_company_data)
    db_session.add(company)
    db_session.commit()

    # Exercise - call the function under test
    result = get_company_by_ticker("AAPL")

    # Verify - check the results
    assert result is not None
    assert result.id == company.id
    assert result.name == "Apple Inc."
```

