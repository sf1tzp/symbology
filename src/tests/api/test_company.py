"""Unit tests for the company routes."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from src.api.routes.companies import router as company_router
from src.api.schemas import Company as CompanySchema
from src.ingestion.database.models import Company as CompanyModel
from src.ingestion.database.base import init_db
from src.tests.conftest import TEST_DATABASE_URL


@pytest.fixture
def test_app():
    """Create a test application with only the company routes for isolated testing."""
    app = FastAPI()
    app.include_router(company_router, prefix="/companies")

    # Initialize the database for testing
    init_db(TEST_DATABASE_URL)

    return app


@pytest.fixture
def client(test_app):
    """Create a test client for the application."""
    return TestClient(test_app)


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return MagicMock()


@pytest.fixture
def mock_company_data():
    """Create a mock company dict."""
    return {
        "id": 1,
        "name": "Test Company",
        "tickers": ["TEST"],  # Changed from ticker to tickers (list) to match schema
        "cik": 1234567890,
        "sic": 1234,
        "description": "A test company",
        "exchanges": ["NYSE"],  # Changed from exchange to exchanges (list) to match schema
        "industry": "Technology",
        "sector": "Information Technology",
        "website": "https://testcompany.com",
        "employees": 100,
        "sic_description": "Software Services",
        "ein": "12-3456789",
        "state_of_incorporation": "DE",
        "fiscal_year_end": "12-31",
        "created_at": "2025-04-15T00:00:00",
        "updated_at": "2025-04-15T01:00:00"
    }


@pytest.fixture
def mock_company_model(mock_company_data):
    """Create a mock company model object."""
    company = MagicMock(spec=CompanyModel)
    for key, value in mock_company_data.items():
        setattr(company, key, value)

    return company


# Test GET /companies/
@patch("src.api.routes.companies.get_db")
@patch("src.api.routes.companies.get_all_companies")
def test_read_companies(mock_get_all_companies, mock_get_db, client, mock_db, mock_company_data):
    """Test retrieving a list of companies."""
    # Set up mocks
    mock_get_db.return_value = mock_db

    # Create a proper company model list that will convert correctly to the response schema
    company_model = MagicMock()
    for key, value in mock_company_data.items():
        setattr(company_model, key, value)
    mock_get_all_companies.return_value = [company_model]

    # Make request
    response = client.get("/companies/")

    # Verify response
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == 1
    assert response.json()[0]["name"] == "Test Company"

    # Verify mock calls - check that it was called with expected parameters
    assert mock_get_all_companies.called
    # Verify the skip and limit parameters
    call_args = mock_get_all_companies.call_args[1]
    assert call_args["skip"] == 0
    assert call_args["limit"] == 100


@patch("src.api.routes.companies.get_db")
@patch("src.api.routes.companies.get_companies_by_ticker")
def test_read_companies_by_ticker(mock_get_companies_by_ticker, mock_get_db, client, mock_db, mock_company_data):
    """Test retrieving companies filtered by ticker."""
    # Set up mocks
    mock_get_db.return_value = mock_db

    # Create a proper company model that will convert correctly to the response schema
    company_model = MagicMock()
    for key, value in mock_company_data.items():
        setattr(company_model, key, value)
    mock_get_companies_by_ticker.return_value = [company_model]

    # Make request
    response = client.get("/companies/?ticker=TEST")

    # Verify response
    assert response.status_code == 200
    assert len(response.json()) == 1
    # Use tickers list instead of ticker field
    assert "TEST" in response.json()[0]["tickers"]

    # Verify mock calls - only validate that it was called and with the right ticker
    assert mock_get_companies_by_ticker.called
    assert mock_get_companies_by_ticker.call_args[0][0] == "TEST"


# Test POST /companies/
@patch("src.api.routes.companies.get_db")
@patch("src.api.routes.companies.create_company")
def test_create_company(mock_create_company, mock_get_db, client, mock_db, mock_company_data):
    """Test creating a new company."""
    # Set up mocks
    mock_get_db.return_value = mock_db

    # Create a proper company model that will convert correctly to the response schema
    company_model = MagicMock()
    for key, value in mock_company_data.items():
        setattr(company_model, key, value)
    mock_create_company.return_value = company_model

    # Prepare test data
    company_data = {
        "name": "New Company",
        "tickers": ["NEW"],  # Fixed to match schema (list)
        "cik": 987654321,    # Changed to int to match schema
        "sic": 4321,         # Changed to int to match schema
        "description": "A new test company",
        "exchanges": ["NASDAQ"],  # Fixed to match schema (list)
        "industry": "Finance",
        "sector": "Financial Services",
        "website": "https://newcompany.com",
        "employees": 200
    }

    # Make request
    response = client.post("/companies/", json=company_data)

    # Verify response
    assert response.status_code == 201
    assert response.json()["name"] == "Test Company"  # From the mock

    # Verify mock calls
    assert mock_create_company.called
    # We can't check the exact properties as it's passed as a dict, not an object with properties
    # So just verify it was called


@patch("src.api.routes.companies.get_db")
@patch("src.api.routes.companies.create_company")
def test_create_company_error(mock_create_company, mock_get_db, client, mock_db):
    """Test error handling when creating a company fails."""
    # Set up mocks
    mock_get_db.return_value = mock_db
    mock_create_company.side_effect = Exception("Database error")

    # Prepare test data
    company_data = {
        "name": "Error Company",
        "ticker": "ERR",
        "cik": "1111111111",
    }

    # Make request
    response = client.post("/companies/", json=company_data)

    # Verify response
    assert response.status_code == 500
    assert "Failed to create company" in response.json()["detail"]


# Test GET /companies/{company_id}
@patch("src.api.routes.companies.get_db")
@patch("src.api.routes.companies.get_company_by_id")
def test_read_company(mock_get_company_by_id, mock_get_db, client, mock_db, mock_company_data):
    """Test retrieving a specific company by ID."""
    # Set up mocks
    mock_get_db.return_value = mock_db

    # Create a proper company model that will convert correctly to the response schema
    company_model = MagicMock()
    for key, value in mock_company_data.items():
        setattr(company_model, key, value)
    mock_get_company_by_id.return_value = company_model

    # Make request
    response = client.get("/companies/1")

    # Verify response
    assert response.status_code == 200
    assert response.json()["id"] == 1
    assert response.json()["name"] == "Test Company"

    # Verify mock calls - check that it was called with the right company ID
    assert mock_get_company_by_id.called
    assert mock_get_company_by_id.call_args[0][0] == 1


@patch("src.api.routes.companies.get_db")
@patch("src.api.routes.companies.get_company_by_id")
def test_read_company_not_found(mock_get_company_by_id, mock_get_db, client, mock_db):
    """Test error handling when company is not found."""
    # Set up mocks
    mock_get_db.return_value = mock_db
    mock_get_company_by_id.return_value = None

    # Make request
    response = client.get("/companies/999")

    # Verify response
    assert response.status_code == 404
    assert response.json()["detail"] == "Company not found"


# Test PUT /companies/{company_id}
@patch("src.api.routes.companies.get_db")
@patch("src.api.routes.companies.get_company_by_id")
@patch("src.api.routes.companies.update_company")
def test_update_company(mock_update_company, mock_get_company_by_id, mock_get_db, client, mock_db, mock_company_data):
    """Test updating a company."""
    # Set up mocks
    mock_get_db.return_value = mock_db

    # Create a proper company model that will convert correctly to the response schema
    company_model = MagicMock()
    for key, value in mock_company_data.items():
        setattr(company_model, key, value)
    mock_get_company_by_id.return_value = company_model
    mock_update_company.return_value = company_model

    # Prepare update data
    update_data = {
        "name": "Updated Company",
        "description": "An updated company description"
    }

    # Make request
    response = client.put("/companies/1", json=update_data)

    # Verify response
    assert response.status_code == 200
    assert response.json()["id"] == 1

    # Verify mock calls - check that they were called with the right parameters
    assert mock_get_company_by_id.called
    assert mock_update_company.called
    assert mock_get_company_by_id.call_args[0][0] == 1


@patch("src.api.routes.companies.get_db")
@patch("src.api.routes.companies.get_company_by_id")
def test_update_company_not_found(mock_get_company_by_id, mock_get_db, client, mock_db):
    """Test error handling when updating a non-existent company."""
    # Set up mocks
    mock_get_db.return_value = mock_db
    mock_get_company_by_id.return_value = None

    # Prepare update data
    update_data = {"name": "Not Found Company"}

    # Make request
    response = client.put("/companies/999", json=update_data)

    # Verify response
    assert response.status_code == 404
    assert response.json()["detail"] == "Company not found"


# Test DELETE /companies/{company_id}
@patch("src.api.routes.companies.get_db")
@patch("src.api.routes.companies.get_company_by_id")
@patch("src.api.routes.companies.delete_company")
def test_delete_company(mock_delete_company, mock_get_company_by_id, mock_get_db, client, mock_db, mock_company_data):
    """Test deleting a company."""
    # Set up mocks
    mock_get_db.return_value = mock_db

    # Create a proper company model that will convert correctly to the response schema
    company_model = MagicMock()
    for key, value in mock_company_data.items():
        setattr(company_model, key, value)
    mock_get_company_by_id.return_value = company_model
    mock_delete_company.return_value = None

    # Make request
    response = client.delete("/companies/1")

    # Verify response
    assert response.status_code == 204
    assert response.content == b''  # Empty content for 204 response

    # Verify mock calls - only check that they were called, not with exactly what args
    assert mock_get_company_by_id.called
    assert mock_delete_company.called

    # Verify the company ID was correctly passed
    assert mock_get_company_by_id.call_args[0][0] == 1
    assert mock_delete_company.call_args[0][0] == 1


@patch("src.api.routes.companies.get_db")
@patch("src.api.routes.companies.get_company_by_id")
def test_delete_company_not_found(mock_get_company_by_id, mock_get_db, client, mock_db):
    """Test error handling when deleting a non-existent company."""
    # Set up mocks
    mock_get_db.return_value = mock_db
    mock_get_company_by_id.return_value = None

    # Make request
    response = client.delete("/companies/999")

    # Verify response
    assert response.status_code == 404
    assert response.json()["detail"] == "Company not found"