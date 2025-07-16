"""Tests for the aggregates API endpoints."""
from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient
from src.api.main import app
from src.database.aggregates import Aggregate
from src.database.completions import Completion
from src.database.documents import Document, DocumentType

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

    @patch("src.api.routes.aggregates.get_aggregate")
    def test_get_aggregate_source_completions_found(self, mock_get_aggregate):
        """Test retrieving source completions for an aggregate when they exist."""
        test_aggregate_id = uuid4()
        test_completion_id_1 = uuid4()
        test_completion_id_2 = uuid4()
        test_doc_id_1 = uuid4()
        test_doc_id_2 = uuid4()
        test_prompt_id = uuid4()

        # Create mock completions with source documents
        mock_completion_1 = Completion(
            id=test_completion_id_1,
            system_prompt_id=test_prompt_id,
            model="gpt-4",
            temperature=0.7,
            top_p=1.0,
            num_ctx=4096,
            created_at=datetime(2023, 12, 25, 12, 30, 45),
            total_duration=2.5,
            source_documents=[Document(id=test_doc_id_1)]
        )

        mock_completion_2 = Completion(
            id=test_completion_id_2,
            model="gpt-3.5-turbo",
            temperature=0.5,
            created_at=datetime(2023, 12, 25, 12, 35, 15),
            total_duration=1.8,
            source_documents=[Document(id=test_doc_id_2)]
        )

        # Create mock aggregate with source completions
        mock_aggregate = MagicMock()
        mock_aggregate.id = test_aggregate_id
        mock_aggregate.source_completions = [mock_completion_1, mock_completion_2]

        mock_get_aggregate.return_value = mock_aggregate

        # Make the API call
        response = client.get(f"/api/aggregates/{test_aggregate_id}/completions")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

        # Check first completion
        completion_1_data = next(item for item in data if item["id"] == str(test_completion_id_1))
        assert completion_1_data["model"] == "gpt-4"
        assert completion_1_data["temperature"] == 0.7
        assert completion_1_data["system_prompt_id"] == str(test_prompt_id)
        assert len(completion_1_data["source_documents"]) == 1
        assert completion_1_data["source_documents"][0] == str(test_doc_id_1)

        # Check second completion
        completion_2_data = next(item for item in data if item["id"] == str(test_completion_id_2))
        assert completion_2_data["model"] == "gpt-3.5-turbo"
        assert completion_2_data["temperature"] == 0.5
        assert completion_2_data["system_prompt_id"] is None
        assert len(completion_2_data["source_documents"]) == 1
        assert completion_2_data["source_documents"][0] == str(test_doc_id_2)

        # Verify the mock was called with the correct arguments
        mock_get_aggregate.assert_called_once_with(test_aggregate_id)

    @patch("src.api.routes.aggregates.get_aggregate")
    def test_get_aggregate_source_completions_aggregate_not_found(self, mock_get_aggregate):
        """Test retrieving source completions when aggregate doesn't exist."""
        test_aggregate_id = uuid4()

        # Setup the mock to return None (aggregate not found)
        mock_get_aggregate.return_value = None

        # Make the API call
        response = client.get(f"/api/aggregates/{test_aggregate_id}/completions")

        # Assertions
        assert response.status_code == 404
        assert f"Aggregate with ID {test_aggregate_id} not found" in response.json()["detail"]

        # Verify the mock was called with the correct arguments
        mock_get_aggregate.assert_called_once_with(test_aggregate_id)

    @patch("src.api.routes.aggregates.get_aggregate")
    def test_get_aggregate_source_completions_no_completions(self, mock_get_aggregate):
        """Test retrieving source completions when aggregate has no source completions."""
        test_aggregate_id = uuid4()

        # Create mock aggregate with no source completions
        mock_aggregate = MagicMock()
        mock_aggregate.id = test_aggregate_id
        mock_aggregate.source_completions = []

        mock_get_aggregate.return_value = mock_aggregate

        # Make the API call
        response = client.get(f"/api/aggregates/{test_aggregate_id}/completions")

        # Assertions
        assert response.status_code == 404
        assert f"No source completions found for aggregate {test_aggregate_id}" in response.json()["detail"]

        # Verify the mock was called with the correct arguments
        mock_get_aggregate.assert_called_once_with(test_aggregate_id)

    def test_get_aggregate_source_completions_invalid_uuid(self):
        """Test retrieving source completions with invalid UUID format."""
        invalid_uuid = "not-a-valid-uuid"

        # Make the API call
        response = client.get(f"/api/aggregates/{invalid_uuid}/completions")

        # Assertions
        assert response.status_code == 422
        assert "uuid_parsing" in str(response.json())

    @patch("src.api.routes.aggregates.get_aggregate")
    def test_get_aggregate_source_completions_database_error(self, mock_get_aggregate):
        """Test error handling when database query fails."""
        test_aggregate_id = uuid4()

        # Setup the mock to raise a database exception
        mock_get_aggregate.side_effect = Exception("Database connection error")

        # Make the API call
        response = client.get(f"/api/aggregates/{test_aggregate_id}/completions")

        # Assertions
        assert response.status_code == 500
        assert f"Internal server error while retrieving source completions for aggregate {test_aggregate_id}" in response.json()["detail"]

        # Verify the mock was called with the correct arguments
        mock_get_aggregate.assert_called_once_with(test_aggregate_id)