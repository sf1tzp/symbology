"""Tests for the aggregates API endpoints."""
from datetime import datetime
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

from src.api.main import app
from src.database.aggregates import Aggregate
from src.database.documents import DocumentType

client = TestClient(app)

# Sample data for tests
SAMPLE_COMPANY_ID = uuid4()
SAMPLE_AGGREGATE_ID = uuid4()

# Sample aggregate data
SAMPLE_AGGREGATE_DATA = [
    {
        "id": uuid4(),
        "company_id": SAMPLE_COMPANY_ID,
        "document_type": DocumentType.MDA,
        "created_at": datetime(2023, 12, 25, 12, 30, 45),
        "total_duration": 5.2,
        "content": "This company has shown strong financial performance in the Management Discussion and Analysis section...",
        "model": "gpt-4",
        "temperature": 0.7,
        "top_p": 1.0,
        "num_ctx": 4096,
        "system_prompt_id": uuid4()
    },
    {
        "id": uuid4(),
        "company_id": SAMPLE_COMPANY_ID,
        "document_type": DocumentType.RISK_FACTORS,
        "created_at": datetime(2023, 12, 25, 12, 35, 15),
        "total_duration": 3.8,
        "content": "The primary risk factors for this company include market volatility, regulatory changes...",
        "model": "gpt-4",
        "temperature": 0.7,
        "top_p": 1.0,
        "num_ctx": 4096,
        "system_prompt_id": uuid4()
    },
    {
        "id": uuid4(),
        "company_id": SAMPLE_COMPANY_ID,
        "document_type": DocumentType.DESCRIPTION,
        "created_at": datetime(2023, 12, 25, 12, 40, 30),
        "total_duration": 2.1,
        "content": "Company description aggregate summarizing the business operations and strategy...",
        "model": "gpt-4",
        "temperature": 0.7,
        "top_p": 1.0,
        "num_ctx": 4096,
        "system_prompt_id": uuid4()
    }
]


class TestAggregatesApi:
    """Test class for Aggregates API endpoints."""

    @patch("src.api.routes.aggregates.get_recent_aggregates_by_ticker")
    def test_get_company_aggregates_by_ticker_found(self, mock_get_aggregates):
        """Test retrieving aggregates by ticker when they exist."""
        # Create mock aggregate objects
        mock_aggregates = []
        for data in SAMPLE_AGGREGATE_DATA:
            mock_aggregate = Aggregate()
            for key, value in data.items():
                setattr(mock_aggregate, key, value)
            mock_aggregates.append(mock_aggregate)

        # Setup the mock to return our sample aggregates
        mock_get_aggregates.return_value = mock_aggregates

        # Make the API call
        response = client.get("/api/aggregates/by-ticker/AAPL")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

        # Check first aggregate (MDA) - using actual enum value
        mda_aggregate = next(item for item in data if item["document_type"] == "management_discussion")
        assert mda_aggregate["content"].startswith("This company has shown strong financial performance")
        assert mda_aggregate["model"] == "gpt-4"
        assert mda_aggregate["temperature"] == 0.7

        # Check second aggregate (RISK_FACTORS) - using actual enum value
        risk_aggregate = next(item for item in data if item["document_type"] == "risk_factors")
        assert risk_aggregate["content"].startswith("The primary risk factors")
        assert risk_aggregate["total_duration"] == 3.8

        # Check third aggregate (DESCRIPTION) - using actual enum value
        desc_aggregate = next(item for item in data if item["document_type"] == "business_description")
        assert desc_aggregate["content"].startswith("Company description aggregate")
        assert desc_aggregate["total_duration"] == 2.1

        # Verify the mock was called with the correct arguments
        mock_get_aggregates.assert_called_once_with("AAPL")

    @patch("src.api.routes.aggregates.get_recent_aggregates_by_ticker")
    def test_get_company_aggregates_by_ticker_not_found(self, mock_get_aggregates):
        """Test retrieving aggregates by ticker when none exist."""
        # Setup the mock to return an empty list
        mock_get_aggregates.return_value = []

        # Make the API call
        response = client.get("/api/aggregates/by-ticker/NONEXISTENT")

        # Assertions
        assert response.status_code == 404
        assert response.json()["detail"] == "No aggregates found for company with ticker NONEXISTENT"

        # Verify the mock was called with the correct arguments
        mock_get_aggregates.assert_called_once_with("NONEXISTENT")

    @patch("src.api.routes.aggregates.get_recent_aggregates_by_ticker")
    def test_get_company_aggregates_by_ticker_single_document_type(self, mock_get_aggregates):
        """Test retrieving aggregates when only one document type exists."""
        # Create a single mock aggregate
        mock_aggregate = Aggregate()
        mock_aggregate.id = SAMPLE_AGGREGATE_DATA[0]["id"]
        mock_aggregate.company_id = SAMPLE_AGGREGATE_DATA[0]["company_id"]
        mock_aggregate.document_type = SAMPLE_AGGREGATE_DATA[0]["document_type"]
        mock_aggregate.created_at = SAMPLE_AGGREGATE_DATA[0]["created_at"]
        mock_aggregate.total_duration = SAMPLE_AGGREGATE_DATA[0]["total_duration"]
        mock_aggregate.content = SAMPLE_AGGREGATE_DATA[0]["content"]
        mock_aggregate.model = SAMPLE_AGGREGATE_DATA[0]["model"]
        mock_aggregate.temperature = SAMPLE_AGGREGATE_DATA[0]["temperature"]
        mock_aggregate.top_p = SAMPLE_AGGREGATE_DATA[0]["top_p"]
        mock_aggregate.num_ctx = SAMPLE_AGGREGATE_DATA[0]["num_ctx"]
        mock_aggregate.system_prompt_id = SAMPLE_AGGREGATE_DATA[0]["system_prompt_id"]

        mock_get_aggregates.return_value = [mock_aggregate]

        # Make the API call
        response = client.get("/api/aggregates/by-ticker/GOOGL")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["document_type"] == "management_discussion"  # Use actual enum value
        assert data[0]["company_id"] == str(SAMPLE_COMPANY_ID)
        assert data[0]["model"] == "gpt-4"

        # Verify the mock was called with the correct arguments
        mock_get_aggregates.assert_called_once_with("GOOGL")

    @patch("src.api.routes.aggregates.get_recent_aggregates_by_ticker")
    def test_get_company_aggregates_with_null_document_type(self, mock_get_aggregates):
        """Test retrieving aggregates when document_type is None."""
        # Create mock aggregate with None document_type
        mock_aggregate = Aggregate()
        mock_aggregate.id = uuid4()
        mock_aggregate.company_id = SAMPLE_COMPANY_ID
        mock_aggregate.document_type = None
        mock_aggregate.created_at = datetime(2023, 12, 25, 12, 30, 45)
        mock_aggregate.total_duration = 5.2
        mock_aggregate.content = "Aggregate with no specific document type"
        mock_aggregate.model = "gpt-4"
        mock_aggregate.temperature = 0.7
        mock_aggregate.top_p = 1.0
        mock_aggregate.num_ctx = 4096
        mock_aggregate.system_prompt_id = uuid4()

        mock_get_aggregates.return_value = [mock_aggregate]

        # Make the API call
        response = client.get("/api/aggregates/by-ticker/TEST")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["document_type"] is None
        assert data[0]["content"] == "Aggregate with no specific document type"

        # Verify the mock was called with the correct arguments
        mock_get_aggregates.assert_called_once_with("TEST")

    @patch("src.api.routes.aggregates.get_recent_aggregates_by_ticker")
    def test_get_company_aggregates_with_optional_fields_none(self, mock_get_aggregates):
        """Test retrieving aggregates when optional fields are None."""
        # Create mock aggregate with minimal required fields
        mock_aggregate = Aggregate()
        mock_aggregate.id = uuid4()
        mock_aggregate.company_id = SAMPLE_COMPANY_ID
        mock_aggregate.document_type = DocumentType.MDA
        mock_aggregate.created_at = datetime(2023, 12, 25, 12, 30, 45)
        mock_aggregate.total_duration = None
        mock_aggregate.content = None
        mock_aggregate.model = "gpt-3.5-turbo"
        mock_aggregate.temperature = None
        mock_aggregate.top_p = None
        mock_aggregate.num_ctx = None
        mock_aggregate.system_prompt_id = None

        mock_get_aggregates.return_value = [mock_aggregate]

        # Make the API call
        response = client.get("/api/aggregates/by-ticker/MINIMAL")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["total_duration"] is None
        assert data[0]["content"] is None
        assert data[0]["temperature"] is None
        assert data[0]["top_p"] is None
        assert data[0]["num_ctx"] is None
        assert data[0]["system_prompt_id"] is None
        assert data[0]["model"] == "gpt-3.5-turbo"

        # Verify the mock was called with the correct arguments
        mock_get_aggregates.assert_called_once_with("MINIMAL")

    @patch("src.api.routes.aggregates.get_recent_aggregates_by_ticker")
    def test_get_company_aggregates_database_error(self, mock_get_aggregates):
        """Test error handling when database query fails."""
        # Setup the mock to raise a database exception
        mock_get_aggregates.side_effect = Exception("Database connection error")

        # Make the API call
        response = client.get("/api/aggregates/by-ticker/ERROR")

        # Assertions
        assert response.status_code == 500
        assert "Internal server error while retrieving aggregates for ERROR" in response.json()["detail"]

        # Verify the mock was called with the correct arguments
        mock_get_aggregates.assert_called_once_with("ERROR")

    def test_get_company_aggregates_ticker_with_special_characters(self):
        """Test retrieving aggregates with ticker containing special characters."""
        with patch("src.api.routes.aggregates.get_recent_aggregates_by_ticker") as mock_get_aggregates:
            # Setup the mock to return empty list
            mock_get_aggregates.return_value = []

            # Make the API call with special characters in ticker
            response = client.get("/api/aggregates/by-ticker/BRK.A")

            # Assertions
            assert response.status_code == 404
            assert "No aggregates found for company with ticker BRK.A" in response.json()["detail"]

            # Verify the mock was called with the ticker including special characters
            mock_get_aggregates.assert_called_once_with("BRK.A")

    def test_get_company_aggregates_case_sensitive_ticker(self):
        """Test that ticker matching is case sensitive."""
        with patch("src.api.routes.aggregates.get_recent_aggregates_by_ticker") as mock_get_aggregates:
            # Setup the mock to return empty list
            mock_get_aggregates.return_value = []

            # Make the API call with lowercase ticker
            response = client.get("/api/aggregates/by-ticker/aapl")

            # Assertions
            assert response.status_code == 404

            # Verify the mock was called with the exact case provided
            mock_get_aggregates.assert_called_once_with("aapl")

    @patch("src.api.routes.aggregates.get_recent_aggregates_by_ticker")
    def test_get_company_aggregates_unicode_ticker(self, mock_get_aggregates):
        """Test retrieving aggregates with unicode characters in ticker."""
        # Setup the mock to return empty list
        mock_get_aggregates.return_value = []

        # Make the API call with unicode characters
        response = client.get("/api/aggregates/by-ticker/TEST™")

        # Assertions
        assert response.status_code == 404
        assert "No aggregates found for company with ticker TEST™" in response.json()["detail"]

        # Verify the mock was called with the unicode ticker
        mock_get_aggregates.assert_called_once_with("TEST™")

    @patch("src.api.routes.aggregates.get_recent_aggregates_by_ticker")
    def test_get_company_aggregates_preserves_order(self, mock_get_aggregates):
        """Test that the API preserves the order returned by the database function."""
        # Create mock aggregates in specific order
        mock_aggregates = []
        for i, doc_type in enumerate([DocumentType.DESCRIPTION, DocumentType.MDA, DocumentType.RISK_FACTORS]):
            mock_aggregate = Aggregate()
            mock_aggregate.id = uuid4()
            mock_aggregate.company_id = SAMPLE_COMPANY_ID
            mock_aggregate.document_type = doc_type
            mock_aggregate.created_at = datetime(2023, 12, 25, 12, 30 + i, 45)
            mock_aggregate.content = f"Content for {doc_type.value}"
            mock_aggregate.model = "gpt-4"
            mock_aggregates.append(mock_aggregate)

        mock_get_aggregates.return_value = mock_aggregates

        # Make the API call
        response = client.get("/api/aggregates/by-ticker/ORDER")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

        # Verify order is preserved - using actual enum values
        assert data[0]["document_type"] == "business_description"  # DocumentType.DESCRIPTION.value
        assert data[1]["document_type"] == "management_discussion"  # DocumentType.MDA.value
        assert data[2]["document_type"] == "risk_factors"  # DocumentType.RISK_FACTORS.value

        # Verify the mock was called with the correct arguments
        mock_get_aggregates.assert_called_once_with("ORDER")