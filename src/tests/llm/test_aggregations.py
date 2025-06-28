"""Tests for the aggregations module."""
from datetime import datetime
from unittest.mock import Mock, mock_open, patch
from uuid import uuid4

import pytest

from src.database.documents import DocumentType
from src.llm.aggregations import (
    _generate_single_aggregate_summary,
    create_document_type_aggregate,
    generate_aggregate_summaries,
    generate_company_summary,
    get_aggregates_summary_report,
    process_all_aggregates,
    save_aggregate_markdown,
    verify_company_summary,
)


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
    @patch('src.llm.aggregations.get_prompt_by_name')
    @patch('src.llm.aggregations.get_chat_response')
    @patch('src.llm.aggregations.get_company_by_ticker')
    @patch('src.llm.aggregations.save_aggregate_markdown')
    def test_success_with_output_dir(
        self,
        mock_save_markdown,
        mock_get_company,
        mock_get_chat_response,
        mock_get_prompt,
        mock_create_aggregate,
        mock_company,
        mock_llm_response,
        mock_prompt
    ):
        """Test successful aggregate creation with output directory."""
        # Setup mocks
        mock_get_company.return_value = mock_company
        mock_get_chat_response.return_value = mock_llm_response
        mock_get_prompt.return_value = mock_prompt

        created_aggregate = Mock()
        created_aggregate.id = uuid4()
        created_aggregate.model = "qwen3:14b"
        created_aggregate.total_duration = 5.0
        created_aggregate.content = "Generated content"
        mock_create_aggregate.return_value = created_aggregate

        # Test data
        client = Mock()
        completion_data = {"2023-12-31": "Test completion content"}
        completion_ids = [1, 2, 3]

        # Execute
        result = create_document_type_aggregate(
            client=client,
            ticker="AAPL",
            document_type=DocumentType.MDA,
            completion_data=completion_data,
            completion_ids=completion_ids,
            model="qwen3:14b",
            output_dir="test_outputs"
        )

        # Verify
        assert result == created_aggregate
        mock_get_company.assert_called_once_with("AAPL")
        mock_get_chat_response.assert_called_once()
        mock_save_markdown.assert_called_once_with(
            "AAPL", DocumentType.MDA, mock_llm_response.message.content, "test_outputs"
        )
        mock_create_aggregate.assert_called_once()

        # Verify aggregate data structure
        call_args = mock_create_aggregate.call_args[0][0]
        assert call_args['model'] == "qwen3:14b"
        assert call_args['company_id'] == mock_company.id
        assert call_args['document_type'] == DocumentType.MDA
        assert call_args['completion_ids'] == completion_ids

    @patch('src.llm.aggregations.create_aggregate')
    @patch('src.llm.aggregations.get_prompt_by_name')
    @patch('src.llm.aggregations.get_chat_response')
    @patch('src.llm.aggregations.get_company_by_ticker')
    def test_success_without_output_dir(
        self,
        mock_get_company,
        mock_get_chat_response,
        mock_get_prompt,
        mock_create_aggregate,
        mock_company,
        mock_llm_response,
        mock_prompt
    ):
        """Test successful aggregate creation without output directory."""
        # Setup mocks
        mock_get_company.return_value = mock_company
        mock_get_chat_response.return_value = mock_llm_response
        mock_get_prompt.return_value = mock_prompt

        created_aggregate = Mock()
        created_aggregate.id = uuid4()
        created_aggregate.model = "qwen3:14b"
        created_aggregate.total_duration = 5.0
        created_aggregate.content = "Generated content"
        mock_create_aggregate.return_value = created_aggregate

        # Execute
        result = create_document_type_aggregate(
            client=Mock(),
            ticker="AAPL",
            document_type=DocumentType.RISK_FACTORS,
            completion_data={"2023-12-31": "Test content"},
            completion_ids=[1]
        )

        # Verify
        assert result == created_aggregate
        mock_create_aggregate.assert_called_once()

    @patch('src.llm.aggregations.get_company_by_ticker')
    def test_error_handling(self, mock_get_company):
        """Test error handling when company lookup fails."""
        # Setup mock to raise exception
        mock_get_company.side_effect = Exception("Company not found")

        # Execute
        result = create_document_type_aggregate(
            client=Mock(),
            ticker="INVALID",
            document_type=DocumentType.MDA,
            completion_data={},
            completion_ids=[]
        )

        # Verify
        assert result is None


class TestProcessAllAggregates:
    """Test process_all_aggregates function."""

    @patch('src.llm.aggregations.create_document_type_aggregate')
    def test_process_multiple_types(self, mock_create_aggregate):
        """Test processing multiple document types."""
        # Setup mock return values
        mock_mda_aggregate = Mock()
        mock_risk_aggregate = Mock()
        mock_create_aggregate.side_effect = [mock_mda_aggregate, mock_risk_aggregate, None]

        # Test data
        completion_ids_by_type = {
            "mda": [1, 2],
            "risk_factors": [3, 4],
            "description": [5, 6]
        }
        completion_data_by_type = {
            "mda": {"2023-12-31": "MDA content"},
            "risk_factors": {"2023-12-31": "Risk factors content"},
            "description": {"2023-12-31": "Description content"}
        }

        # Execute
        result = process_all_aggregates(
            client=Mock(),
            ticker="AAPL",
            completion_ids_by_type=completion_ids_by_type,
            completion_data_by_type=completion_data_by_type
        )

        # Verify
        assert len(result) == 2  # Only successful aggregates
        assert "mda" in result
        assert "risk_factors" in result
        assert "description" not in result  # Failed to create
        assert result["mda"] == mock_mda_aggregate
        assert result["risk_factors"] == mock_risk_aggregate

        # Verify function was called for each type
        assert mock_create_aggregate.call_count == 3

    @patch('src.llm.aggregations.create_document_type_aggregate')
    def test_empty_completion_ids(self, mock_create_aggregate):
        """Test handling of empty completion IDs."""
        completion_ids_by_type = {
            "mda": [],
            "risk_factors": [1, 2]
        }
        completion_data_by_type = {
            "mda": {},
            "risk_factors": {"2023-12-31": "Content"}
        }

        mock_create_aggregate.return_value = Mock()

        # Execute
        result = process_all_aggregates(
            client=Mock(),
            ticker="AAPL",
            completion_ids_by_type=completion_ids_by_type,
            completion_data_by_type=completion_data_by_type
        )

        # Verify - only risk_factors should be processed
        assert len(result) == 1
        assert "risk_factors" in result
        mock_create_aggregate.assert_called_once()


class TestSaveAggregateMarkdown:
    """Test save_aggregate_markdown function."""

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.makedirs')
    def test_save_with_custom_output_dir(self, mock_makedirs, mock_file):
        """Test saving markdown with custom output directory."""
        # Execute
        save_aggregate_markdown(
            ticker="AAPL",
            document_type=DocumentType.MDA,
            content="Test markdown content",
            output_dir="custom_outputs"
        )

        # Verify
        mock_makedirs.assert_called_once_with("custom_outputs", exist_ok=True)
        mock_file.assert_called_once_with("custom_outputs/mda.md", 'w')
        mock_file().write.assert_called_once_with("Test markdown content")

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.makedirs')
    def test_save_with_default_output_dir(self, mock_makedirs, mock_file):
        """Test saving markdown with default output directory."""
        # Execute
        save_aggregate_markdown(
            ticker="AAPL",
            document_type=DocumentType.RISK_FACTORS,
            content="Risk factors content"
        )

        # Verify
        mock_makedirs.assert_called_once_with("outputs/AAPL", exist_ok=True)
        mock_file.assert_called_once_with("outputs/AAPL/risk_factors.md", 'w')

    @patch('builtins.open', side_effect=IOError("Permission denied"))
    @patch('os.makedirs')
    def test_save_error_handling(self, mock_makedirs, mock_file):
        """Test error handling when file save fails."""
        # Execute - should not raise exception
        save_aggregate_markdown(
            ticker="AAPL",
            document_type=DocumentType.DESCRIPTION,
            content="Content"
        )

        # Verify makedirs was called but file write failed gracefully
        mock_makedirs.assert_called_once()


class TestGenerateCompanySummary:
    """Test generate_company_summary function."""

    @patch('src.llm.aggregations.update_company')
    @patch('src.llm.aggregations.get_chat_response')
    @patch('src.llm.aggregations.get_recent_aggregates_by_ticker')
    @patch('src.llm.aggregations.get_company_by_ticker')
    def test_successful_summary_generation(
        self,
        mock_get_company,
        mock_get_aggregates,
        mock_get_chat_response,
        mock_update_company,
        mock_company
    ):
        """Test successful company summary generation."""
        # Setup mocks
        mock_get_company.return_value = mock_company

        mock_aggregate_1 = Mock()
        mock_aggregate_1.document_type = DocumentType.MDA
        mock_aggregate_1.content = "MDA analysis content"

        mock_aggregate_2 = Mock()
        mock_aggregate_2.document_type = DocumentType.RISK_FACTORS
        mock_aggregate_2.content = "Risk factors analysis content"

        mock_get_aggregates.return_value = [mock_aggregate_1, mock_aggregate_2]

        mock_response = Mock()
        mock_response.message.content = "Generated company summary"
        mock_response.total_duration = 3000000000  # 3 seconds
        mock_get_chat_response.return_value = mock_response

        mock_update_company.return_value = mock_company

        # Execute
        result = generate_company_summary(
            client=Mock(),
            ticker="AAPL",
            model="qwen3:14b"
        )

        # Verify
        assert result == "Generated company summary"
        mock_get_company.assert_called_once_with("AAPL")
        mock_get_aggregates.assert_called_once_with("AAPL")
        mock_get_chat_response.assert_called_once()
        mock_update_company.assert_called_once_with(
            mock_company.id,
            {'summary': "Generated company summary"}
        )

    @patch('src.llm.aggregations.get_recent_aggregates_by_ticker')
    @patch('src.llm.aggregations.get_company_by_ticker')
    def test_no_aggregates_found(self, mock_get_company, mock_get_aggregates, mock_company):
        """Test handling when no aggregates are found."""
        mock_get_company.return_value = mock_company
        mock_get_aggregates.return_value = []

        # Execute
        result = generate_company_summary(Mock(), "AAPL")

        # Verify
        assert result is None

    @patch('src.llm.aggregations.get_company_by_ticker')
    def test_error_handling(self, mock_get_company):
        """Test error handling when company lookup fails."""
        mock_get_company.side_effect = Exception("Database error")

        # Execute
        result = generate_company_summary(Mock(), "INVALID")

        # Verify
        assert result is None


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

    @patch('src.llm.aggregations.get_chat_response')
    def test_error_handling(self, mock_get_chat_response):
        """Test error handling when LLM call fails."""
        mock_get_chat_response.side_effect = Exception("LLM API error")

        mock_aggregate = Mock()
        mock_aggregate.id = uuid4()
        mock_aggregate.content = "Content"

        # Execute
        result = _generate_single_aggregate_summary(
            Mock(), mock_aggregate, "management_discussion", "qwen3:14b"
        )

        # Verify
        assert result is False


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

    @patch('src.llm.aggregations.get_recent_aggregates_by_ticker')
    def test_error_handling(self, mock_get_aggregates):
        """Test error handling when aggregates lookup fails."""
        mock_get_aggregates.side_effect = Exception("Database error")

        # Execute
        result = get_aggregates_summary_report("INVALID")

        # Verify
        assert result == {}