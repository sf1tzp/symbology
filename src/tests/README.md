# Symbology Testing Strategy

This directory contains tests for the Symbology application. The tests are organized by functional area and use pytest as the test framework.

## Testing Philosophy

Our testing approach follows these principles:

1. **Isolation**: Each test should run independently without relying on other tests.
2. **Speed**: Tests should execute quickly to enable frequent test runs during development.
3. **Comprehensiveness**: Tests should cover both happy paths and error scenarios.
4. **Readability**: Tests should be easy to understand and maintain.

## Test Structure

The tests are organized into the following directories:

- `db/`: Tests for database models and CRUD operations
- `ingestion/`: Tests for data ingestion functionality

## Test Database

Tests use a dedicated PostgreSQL test database (`symbology-test`) that is created and destroyed during the test session. This ensures tests don't interfere with development or production data.

## Test Fixtures

Common test fixtures are defined in `conftest.py`. These include:

- `db_engine`: Creates a SQLAlchemy engine connected to the test database
- `db_session`: Creates a fresh database session for each test
- `sample_company_data`: Sample data for creating Company objects
- `sample_filing_data`: Sample data for creating Filing objects
- `sample_financial_concept_data`: Sample data for financial concepts
- `sample_balance_sheet_data`: Sample balance sheet values
- `sample_balance_sheet_df`: Sample balance sheet DataFrame for testing

## Mocking in Tests

Several tests in this project use mocking to isolate components and test them independently without relying on external services or systems. We primarily use Python's `unittest.mock` library for this purpose.

### MagicMock and Mock

`MagicMock` is a powerful mocking class that automatically creates attributes and methods as needed, returning new `MagicMock` objects when accessed. This makes it ideal for mocking complex objects like the EDGAR API responses or XBRL objects.

Key features of `MagicMock` used in our tests:

- **Method Chaining**: Allows mocking nested method calls (e.g., `mock_xbrl.statements.balance_sheet.to_dataframe()`)
- **Return Value Configuration**: Setting specific return values with `return_value`
- **Call Tracking**: Verifying that methods were called with the right parameters
- **Call Assertions**: Assertions like `mock_method.assert_called_once_with(expected_args)`

Example from `test_edgar_financials.py`:
```python
# Create mock objects in a chain
mock_xbrl_instance = MagicMock()
mock_balance_sheet = MagicMock()
mock_xbrl.return_value = mock_xbrl_instance
mock_xbrl_instance.statements.balance_sheet.return_value = mock_balance_sheet
mock_balance_sheet.to_dataframe.return_value = sample_dataframe
```

### Patch Decorator

The `@patch` decorator is used to replace objects within a specific scope (like a test method). This allows us to temporarily replace functions or classes with mock objects during test execution.

In our tests, `@patch` is used to:

- Replace external API calls (`get_balance_sheet_values`, `XBRL.from_filing`)
- Avoid actual file system or database access during tests
- Control the behavior of complex dependencies

Example:
```python
@patch('src.python.ingestion.edgar.XBRL.from_filing')
def test_get_balance_sheet_values(self, mock_xbrl):
    # The real XBRL.from_filing is replaced with mock_xbrl for this test
```

### Best Practices for Mocking

Our tests follow these mocking best practices:

1. **Mock at boundaries**: Only mock external services or complex dependencies
2. **Verify interactions**: Assert that mocks were called with expected parameters
3. **Isolate tests**: Each test should work independently regardless of external systems
4. **Be specific**: Mock only what's necessary, no more
5. **Preserve interfaces**: Mocks should behave like the real objects they replace

Mocking has been particularly useful for testing our EDGAR integration without making actual API calls to the SEC servers during tests.

## Implemented Tests

### Database Tests (`db/`)

#### Company Model Tests (`test_company.py`)
- Company creation, retrieval, updating, and deletion
- Unique constraint enforcement (CIK must be unique)
- Ticker-based searching
- Upsert operations (insert or update)
- Conversion to dictionary/JSON

#### Filing Model Tests (`test_filing.py`)
- Filing creation, retrieval, updating, and deletion
- Unique constraint enforcement (accession number must be unique)
- Date-based and type-based searching
- Company-Filing relationship tests
- Upsert operations (insert or update)
- Conversion to dictionary/JSON

#### Financial Data Tests (`test_financials.py`)
- Financial concept creation and label mapping
- Balance sheet value storage and retrieval
- Processing of balance sheet dataframes
- Date-based financial data retrieval
- Relationship tests between financial models
- Concept-to-label mapping verification

### Ingestion Tests (`ingestion/`)

#### Edgar Financial Data Tests (`test_edgar_financials.py`)
- Balance sheet data extraction from EDGAR filings
- Income statement data extraction from EDGAR filings
- Storage of extracted data in the database
- Integration between EDGAR parsing and database storage

## Running Tests

Tests can be run using the following command:

```bash
just test
```

This will execute all tests and report any failures.

## Test Coverage

To generate a test coverage report, run:

```bash
just test-coverage
```

(Note: test-coverage command needs to be implemented in the justfile)