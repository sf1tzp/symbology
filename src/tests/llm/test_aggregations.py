"""Tests for the aggregations module."""
from datetime import datetime
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from src.database.documents import DocumentType
from src.llm.aggregations import (
    _generate_single_aggregate_summary,
    create_document_type_aggregate,
    generate_aggregate_summaries,
    get_aggregates_summary_report,
    verify_company_summary,
)
from src.llm.client import ModelConfig


# Test fixtures
@pytest.fixture
def mock_company():
    """Mock company object."""
    company = Mock()
    company.id = uuid4()
    company.summary = None
    return company


@pytest.fixture
def mock_aggregate():
    """Mock aggregate object."""
    aggregate = Mock()
    aggregate.id = uuid4()
    aggregate.document_type = DocumentType.MDA
    aggregate.content = "Test aggregate content for MDA analysis."
    aggregate.summary = None
    aggregate.model = "qwen3:14b"
    aggregate.created_at = datetime.now()
    aggregate.total_duration = 5.0
    return aggregate


@pytest.fixture
def mock_llm_response():
    """Mock LLM response object."""
    response = Mock()
    response.message.content = "Generated aggregate content from LLM"
    response.total_duration = 5000000000  # 5 seconds in nanoseconds
    response.created_at = datetime.now()
    return response


@pytest.fixture
def mock_prompt():
    """Mock prompt object."""
    prompt = Mock()
    prompt.id = uuid4()
    prompt.name = "aggregate_prompt"
    return prompt


class TestCreateDocumentTypeAggregate:
    """Test create_document_type_aggregate function."""

    @patch('src.llm.aggregations.create_aggregate')
    @patch('src.llm.aggregations.get_chat_response')
    @patch('src.llm.aggregations.format_aggregate_messages')
    def test_successful_aggregate_creation(
        self,
        mock_format_messages,
        mock_get_chat_response,
        mock_create_aggregate,
        mock_llm_response,
    ):
        """Test successful aggregate creation."""
        # Setup mocks
        mock_format_messages.return_value = [{"role": "user", "content": "Test content"}]
        mock_get_chat_response.return_value = mock_llm_response

        created_aggregate = Mock()
        created_aggregate.id = uuid4()
        created_aggregate.model = "qwen3:14b"
        created_aggregate.total_duration = 5.0
        created_aggregate.content = "Generated content"
        mock_create_aggregate.return_value = created_aggregate

        # Create mock completions with required relationships
        mock_completion = Mock()
        mock_document = Mock()
        mock_company = Mock()
        mock_company.ticker = "AAPL"
        mock_document.company = mock_company
        mock_completion.source_documents = [mock_document]

        mock_prompt = Mock()
        mock_model_config = ModelConfig(name="qwen3:14b")

        # Execute
        result = create_document_type_aggregate(
            document_type=DocumentType.MDA,
            completions=[mock_completion],
            prompt=mock_prompt,
            model_config=mock_model_config,
        )

        # Verify
        assert result == created_aggregate
        mock_format_messages.assert_called_once_with(mock_prompt, [mock_completion])
        mock_get_chat_response.assert_called_once()
        mock_create_aggregate.assert_called_once()

        # Verify aggregate data structure
        call_args = mock_create_aggregate.call_args[0][0]
        assert call_args['model'] == "qwen3:14b"
        assert call_args['document_type'] == DocumentType.MDA
        assert call_args['completions'] == [mock_completion]

class TestGenerateAggregateSummaries:
    """Test generate_aggregate_summaries function."""

    @patch('src.llm.aggregations._generate_single_aggregate_summary')
    @patch('src.llm.aggregations.get_recent_aggregates_by_ticker')
    def test_process_multiple_aggregates(self, mock_get_aggregates, mock_generate_single):
        """Test processing multiple aggregates."""
        # Setup mocks
        mock_agg_1 = Mock()
        mock_agg_1.id = uuid4()
        mock_agg_1.document_type = DocumentType.MDA
        mock_agg_1.content = "Long content for MDA that is definitely more than fifty characters long to pass the length check"
        mock_agg_1.summary = None

        mock_agg_2 = Mock()
        mock_agg_2.id = uuid4()
        mock_agg_2.document_type = DocumentType.RISK_FACTORS
        mock_agg_2.content = "Long content for risk factors that is definitely more than fifty characters long"
        mock_agg_2.summary = "Already has summary"

        mock_get_aggregates.return_value = [mock_agg_1, mock_agg_2]
        mock_generate_single.return_value = True

        # Execute
        result = generate_aggregate_summaries(Mock(), "AAPL")

        # Verify
        assert len(result) == 2
        assert result[str(mock_agg_1.id)] is True
        assert result[str(mock_agg_2.id)] is True  # Skipped but marked as success

        # Only first aggregate should be processed (second already has summary)
        mock_generate_single.assert_called_once()

        # Verify the call was made with the correct aggregate and document type
        call_args = mock_generate_single.call_args[0]
        assert call_args[1] == mock_agg_1  # Second argument should be the aggregate
        assert call_args[2] == "management_discussion"  # Third argument should be doc type
        assert call_args[3] == "qwen3:14b"  # Fourth argument should be model

    @patch('src.llm.aggregations.get_recent_aggregates_by_ticker')
    def test_insufficient_content(self, mock_get_aggregates):
        """Test handling of aggregates with insufficient content."""
        mock_agg = Mock()
        mock_agg.id = uuid4()
        mock_agg.document_type = DocumentType.MDA
        mock_agg.content = "Short"  # Too short
        mock_agg.summary = None

        mock_get_aggregates.return_value = [mock_agg]

        # Execute
        result = generate_aggregate_summaries(Mock(), "AAPL")

        # Verify
        assert result[str(mock_agg.id)] is False


class TestGenerateSingleAggregateSummary:
    """Test _generate_single_aggregate_summary function."""

    @patch('src.llm.aggregations.update_aggregate')
    @patch('src.llm.aggregations.get_chat_response')
    def test_successful_summary_generation(self, mock_get_chat_response, mock_update_aggregate):
        """Test successful single aggregate summary generation."""
        # Setup mocks
        mock_response = Mock()
        mock_response.message.content = "Generated summary for aggregate"
        mock_get_chat_response.return_value = mock_response

        mock_aggregate = Mock()
        mock_aggregate.id = uuid4()
        mock_aggregate.content = "Long aggregate content to summarize"

        mock_update_aggregate.return_value = mock_aggregate

        # Execute
        result = _generate_single_aggregate_summary(
            client=Mock(),
            aggregate=mock_aggregate,
            doc_type="management_discussion",
            model="qwen3:14b"
        )

        # Verify
        assert result is True
        mock_get_chat_response.assert_called_once()
        mock_update_aggregate.assert_called_once_with(
            mock_aggregate.id,
            {'summary': "Generated summary for aggregate"}
        )


class TestVerifyCompanySummary:
    """Test verify_company_summary function."""

    @patch('src.llm.aggregations.get_company')
    @patch('src.llm.aggregations.get_company_by_ticker')
    def test_successful_verification(self, mock_get_by_ticker, mock_get_company, mock_company):
        """Test successful company summary verification."""
        mock_get_by_ticker.return_value = mock_company

        refreshed_company = Mock()
        # Make summary longer than 200 characters to test truncation
        refreshed_company.summary = "This is a very long company summary that definitely exceeds the two hundred character limit and should be truncated when creating a preview for display purposes in the verification function test case scenario here."
        mock_get_company.return_value = refreshed_company

        # Execute
        success, preview = verify_company_summary("AAPL")

        # Verify
        assert success is True
        assert len(preview) <= 203  # 200 chars + "..."
        assert preview.endswith("...")

    @patch('src.llm.aggregations.get_company')
    @patch('src.llm.aggregations.get_company_by_ticker')
    def test_successful_verification_short_summary(self, mock_get_by_ticker, mock_get_company, mock_company):
        """Test successful verification with short summary that doesn't need truncation."""
        mock_get_by_ticker.return_value = mock_company

        refreshed_company = Mock()
        refreshed_company.summary = "Short summary"
        mock_get_company.return_value = refreshed_company

        # Execute
        success, preview = verify_company_summary("AAPL")

        # Verify
        assert success is True
        assert preview == "Short summary"
        assert not preview.endswith("...")  # Should not be truncated


class TestGetAggregatesSummaryReport:
    """Test get_aggregates_summary_report function."""

    @patch('src.llm.aggregations.get_recent_aggregates_by_ticker')
    def test_generate_report(self, mock_get_aggregates):
        """Test generating aggregates summary report."""
        # Setup mock aggregates
        mock_agg_1 = Mock()
        mock_agg_1.id = uuid4()
        mock_agg_1.document_type = DocumentType.MDA
        mock_agg_1.summary = "Short summary for MDA"
        mock_agg_1.content = "Longer content for MDA analysis"
        mock_agg_1.model = "qwen3:14b"
        mock_agg_1.created_at = datetime(2023, 12, 31, 12, 0, 0)

        mock_agg_2 = Mock()
        mock_agg_2.id = uuid4()
        mock_agg_2.document_type = DocumentType.RISK_FACTORS
        mock_agg_2.summary = None
        mock_agg_2.content = "Risk factors content"
        mock_agg_2.model = "qwen3:14b"
        mock_agg_2.created_at = datetime(2023, 12, 31, 12, 30, 0)

        mock_get_aggregates.return_value = [mock_agg_1, mock_agg_2]

        # Execute
        result = get_aggregates_summary_report("AAPL")

        # Verify
        assert len(result) == 2
        assert "management_discussion" in result
        assert "risk_factors" in result

        mda_report = result["management_discussion"]
        assert mda_report["id"] == str(mock_agg_1.id)
        assert mda_report["has_summary"] is True
        assert mda_report["summary_length"] == len("Short summary for MDA")
        assert mda_report["content_length"] == len("Longer content for MDA analysis")

        risk_report = result["risk_factors"]
        assert risk_report["has_summary"] is False
        assert risk_report["summary_length"] == 0