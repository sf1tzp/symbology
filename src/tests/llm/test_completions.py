"""Tests for the completions module."""
from datetime import date, datetime
import json
from unittest.mock import Mock, mock_open, patch
from uuid import uuid4

import pytest

from src.database.documents import DocumentType
from src.llm.completions import get_completion_results_by_type, process_company_document_completions, process_document_completion, save_completion_results


# Test fixtures
@pytest.fixture
def mock_company():
    """Mock company object."""
    company = Mock()
    company.id = uuid4()
    company.ticker = "AAPL"
    return company


@pytest.fixture
def mock_filing():
    """Mock filing object."""
    filing = Mock()
    filing.id = uuid4()
    filing.filing_date = date(2023, 12, 31)
    filing.filing_type = "10-K"
    return filing


@pytest.fixture
def mock_document():
    """Mock document object."""
    document = Mock()
    document.id = uuid4()
    document.document_name = "test_document.htm"
    document.document_type = DocumentType.MDA
    document.content = "Test document content for management discussion and analysis."
    return document


@pytest.fixture
def mock_llm_response():
    """Mock LLM response object."""
    response = Mock()
    response.message.content = "Generated completion content from LLM"
    response.total_duration = 3000000000  # 3 seconds in nanoseconds
    response.created_at = datetime.now()
    return response


@pytest.fixture
def mock_completion():
    """Mock completion object."""
    completion = Mock()
    completion.id = uuid4()
    completion.model = "qwen3:4b"
    completion.content = "Generated completion content"
    completion.total_duration = 3.0
    return completion


@pytest.fixture
def mock_prompt():
    """Mock prompt object."""
    prompt = Mock()
    prompt.id = uuid4()
    prompt.name = "mda"
    return prompt


class TestProcessDocumentCompletion:
    """Test process_document_completion function."""

    @patch('src.llm.completions.create_completion')
    @patch('src.llm.completions.get_prompt_by_name')
    @patch('src.llm.completions.get_chat_response')
    @patch('src.llm.completions.format_document_messages')
    def test_successful_completion(
        self,
        mock_format_messages,
        mock_get_chat_response,
        mock_get_prompt,
        mock_create_completion,
        mock_document,
        mock_filing,
        mock_llm_response,
        mock_completion,
        mock_prompt
    ):
        """Test successful document completion processing."""
        # Setup mocks
        mock_format_messages.return_value = [{"role": "user", "content": "Test content"}]
        mock_get_chat_response.return_value = mock_llm_response
        mock_get_prompt.return_value = mock_prompt
        mock_create_completion.return_value = mock_completion

        # Execute
        result, completion_id = process_document_completion(
            client=Mock(),
            document=mock_document,
            filing=mock_filing,
            ticker="AAPL",
            model="qwen3:4b"
        )

        # Verify
        assert result["filing_date"] == str(mock_filing.filing_date)
        assert result["content"] == mock_llm_response.message.content
        assert result["completion_id"] == mock_completion.id
        assert result["document_type"] == mock_document.document_type
        assert result["total_duration"] == 3.0
        assert completion_id == mock_completion.id

        # Verify function calls
        mock_format_messages.assert_called_once_with(mock_document)
        mock_get_chat_response.assert_called_once()
        mock_get_prompt.assert_called_once_with(mock_document.document_type.value)
        mock_create_completion.assert_called_once()

        # Verify completion data structure
        call_args = mock_create_completion.call_args[0][0]
        assert call_args['model'] == "qwen3:4b"
        assert call_args['document_ids'] == [mock_document.id]
        assert call_args['system_prompt_id'] == mock_prompt.id

    @patch('src.llm.completions.format_document_messages')
    def test_error_handling(self, mock_format_messages, mock_document, mock_filing):
        """Test error handling when completion processing fails."""
        # Setup mock to raise exception
        mock_format_messages.side_effect = Exception("Format error")

        # Execute and verify exception is raised
        with pytest.raises(Exception, match="Format error"):
            process_document_completion(
                client=Mock(),
                document=mock_document,
                filing=mock_filing,
                ticker="AAPL"
            )


class TestProcessCompanyDocumentCompletions:
    """Test process_company_document_completions function."""

    @patch('src.llm.completions.save_completion_results')
    @patch('src.llm.completions.process_document_completion')
    @patch('src.llm.completions.get_documents_by_filing')
    @patch('src.llm.completions.get_filings_by_company')
    @patch('src.llm.completions.get_company_by_ticker')
    def test_successful_processing_with_output_dir(
        self,
        mock_get_company,
        mock_get_filings,
        mock_get_documents,
        mock_process_completion,
        mock_save_results,
        mock_company,
        mock_filing
    ):
        """Test successful processing of company documents with output directory."""
        # Setup mocks
        mock_get_company.return_value = mock_company
        mock_get_filings.return_value = [mock_filing]

        # Create mock documents for different types
        mock_doc_mda = Mock()
        mock_doc_mda.id = uuid4()
        mock_doc_mda.document_type = DocumentType.MDA

        mock_doc_risk = Mock()
        mock_doc_risk.id = uuid4()
        mock_doc_risk.document_type = DocumentType.RISK_FACTORS

        mock_doc_desc = Mock()
        mock_doc_desc.id = uuid4()
        mock_doc_desc.document_type = DocumentType.DESCRIPTION

        mock_get_documents.return_value = [mock_doc_mda, mock_doc_risk, mock_doc_desc]

        # Setup completion results
        completion_results = [
            ({"filing_date": "2023-12-31", "content": "MDA content", "completion_id": 1, "document_type": DocumentType.MDA, "total_duration": 3.0}, 1),
            ({"filing_date": "2023-12-31", "content": "Risk content", "completion_id": 2, "document_type": DocumentType.RISK_FACTORS, "total_duration": 2.5}, 2),
            ({"filing_date": "2023-12-31", "content": "Description content", "completion_id": 3, "document_type": DocumentType.DESCRIPTION, "total_duration": 2.0}, 3)
        ]
        mock_process_completion.side_effect = completion_results

        # Execute
        result = process_company_document_completions(
            client=Mock(),
            ticker="AAPL",
            model="qwen3:4b",
            output_dir="test_outputs"
        )

        # Verify
        assert len(result) == 3
        assert "mda" in result
        assert "risk_factors" in result
        assert "description" in result
        assert result["mda"] == [1]
        assert result["risk_factors"] == [2]
        assert result["description"] == [3]

        # Verify function calls
        mock_get_company.assert_called_once_with("AAPL")
        mock_get_filings.assert_called_once_with(company_id=mock_company.id)
        mock_get_documents.assert_called_once_with(mock_filing.id)
        assert mock_process_completion.call_count == 3
        mock_save_results.assert_called_once()

    @patch('src.llm.completions.process_document_completion')
    @patch('src.llm.completions.get_documents_by_filing')
    @patch('src.llm.completions.get_filings_by_company')
    @patch('src.llm.completions.get_company_by_ticker')
    def test_successful_processing_without_output_dir(
        self,
        mock_get_company,
        mock_get_filings,
        mock_get_documents,
        mock_process_completion,
        mock_company,
        mock_filing
    ):
        """Test successful processing without output directory."""
        # Setup mocks
        mock_get_company.return_value = mock_company
        mock_get_filings.return_value = [mock_filing]

        mock_doc = Mock()
        mock_doc.document_type = DocumentType.MDA
        mock_get_documents.return_value = [mock_doc]

        mock_process_completion.return_value = (
            {"filing_date": "2023-12-31", "content": "Content", "completion_id": 1, "document_type": DocumentType.MDA, "total_duration": 3.0},
            1
        )

        # Execute
        result = process_company_document_completions(
            client=Mock(),
            ticker="AAPL"
        )

        # Verify
        assert result["mda"] == [1]

    @patch('src.llm.completions.get_documents_by_filing')
    @patch('src.llm.completions.get_filings_by_company')
    @patch('src.llm.completions.get_company_by_ticker')
    def test_unknown_document_type(
        self,
        mock_get_company,
        mock_get_filings,
        mock_get_documents,
        mock_company,
        mock_filing
    ):
        """Test handling of unknown document types."""
        # Setup mocks
        mock_get_company.return_value = mock_company
        mock_get_filings.return_value = [mock_filing]

        # Create mock document with unknown type
        mock_doc = Mock()
        mock_doc.document_type = "UNKNOWN_TYPE"
        mock_get_documents.return_value = [mock_doc]

        with patch('src.llm.completions.process_document_completion') as mock_process:
            mock_process.return_value = (
                {"filing_date": "2023-12-31", "content": "Content", "completion_id": 1, "document_type": "UNKNOWN_TYPE", "total_duration": 3.0},
                1
            )

            # Execute
            result = process_company_document_completions(
                client=Mock(),
                ticker="AAPL"
            )

            # Verify that unknown types don't get added to completion_ids_by_type
            assert all(len(ids) == 0 for ids in result.values())


class TestSaveCompletionResults:
    """Test save_completion_results function."""

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.makedirs')
    @patch('json.dump')
    def test_save_with_custom_output_dir(self, mock_json_dump, mock_makedirs, mock_file):
        """Test saving results with custom output directory."""
        # Test data
        descriptions = {"2023-12-31": "Description content"}
        risk_factors = {"2023-12-31": "Risk factors content"}
        mdas = {"2023-12-31": "MDA content"}

        # Execute
        save_completion_results(
            ticker="AAPL",
            descriptions=descriptions,
            risk_factors=risk_factors,
            mdas=mdas,
            output_dir="custom_outputs"
        )

        # Verify
        mock_makedirs.assert_called_once_with("custom_outputs", exist_ok=True)
        assert mock_file.call_count == 3
        assert mock_json_dump.call_count == 3

        # Verify file paths
        expected_calls = [
            "custom_outputs/mdas.json",
            "custom_outputs/risk_factors.json",
            "custom_outputs/descriptions.json"
        ]
        actual_calls = [call[0][0] for call in mock_file.call_args_list]
        for expected_path in expected_calls:
            assert expected_path in actual_calls

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.makedirs')
    @patch('json.dump')
    def test_save_with_default_output_dir(self, mock_json_dump, mock_makedirs, mock_file):
        """Test saving results with default output directory."""
        # Execute
        save_completion_results(
            ticker="AAPL",
            descriptions={},
            risk_factors={},
            mdas={}
        )

        # Verify
        mock_makedirs.assert_called_once_with("outputs/AAPL", exist_ok=True)

    @patch('builtins.open', side_effect=IOError("Permission denied"))
    @patch('os.makedirs')
    def test_save_error_handling(self, mock_makedirs, mock_file):
        """Test error handling when file save fails."""
        # Execute - should not raise exception
        save_completion_results(
            ticker="AAPL",
            descriptions={"2023-12-31": "content"},
            risk_factors={},
            mdas={}
        )

        # Verify makedirs was called but file operations failed gracefully
        mock_makedirs.assert_called_once()


class TestGetCompletionResultsByType:
    """Test get_completion_results_by_type function."""

    @patch('builtins.open', new_callable=mock_open, read_data='{"2023-12-31": "Test content"}')
    @patch('json.load')
    def test_successful_load(self, mock_json_load, mock_file):
        """Test successful loading of completion results."""
        # Setup mock
        expected_data = {"2023-12-31": "Test MDA content"}
        mock_json_load.return_value = expected_data

        # Execute
        result = get_completion_results_by_type("AAPL", DocumentType.MDA)

        # Verify
        assert result == expected_data
        mock_file.assert_called_once_with("outputs/AAPL/mdas.json", 'r')
        mock_json_load.assert_called_once()

    @patch('builtins.open', new_callable=mock_open, read_data='{"2023-12-31": "Risk content"}')
    @patch('json.load')
    def test_risk_factors_file_mapping(self, mock_json_load, mock_file):
        """Test correct file mapping for risk factors."""
        mock_json_load.return_value = {"2023-12-31": "Risk content"}

        # Execute
        get_completion_results_by_type("AAPL", DocumentType.RISK_FACTORS)

        # Verify correct file path
        mock_file.assert_called_once_with("outputs/AAPL/risk_factors.json", 'r')

    @patch('builtins.open', new_callable=mock_open, read_data='{"2023-12-31": "Description content"}')
    @patch('json.load')
    def test_description_file_mapping(self, mock_json_load, mock_file):
        """Test correct file mapping for descriptions."""
        mock_json_load.return_value = {"2023-12-31": "Description content"}

        # Execute
        get_completion_results_by_type("AAPL", DocumentType.DESCRIPTION)

        # Verify correct file path
        mock_file.assert_called_once_with("outputs/AAPL/descriptions.json", 'r')

    def test_unsupported_document_type(self):
        """Test handling of unsupported document types."""
        # Create a mock document type that doesn't exist in the mapping
        with pytest.raises(ValueError, match="Unsupported document type"):
            get_completion_results_by_type("AAPL", "INVALID_TYPE")

    @patch('builtins.open', side_effect=FileNotFoundError("File not found"))
    def test_file_not_found(self, mock_file):
        """Test handling when completion results file doesn't exist."""
        # Execute
        result = get_completion_results_by_type("AAPL", DocumentType.MDA)

        # Verify
        assert result == {}

    @patch('builtins.open', side_effect=json.JSONDecodeError("Invalid JSON", "doc", 0))
    def test_json_decode_error(self, mock_file):
        """Test handling when JSON file is corrupted."""
        # Execute
        result = get_completion_results_by_type("AAPL", DocumentType.MDA)

        # Verify
        assert result == {}

    @patch('builtins.open', side_effect=Exception("General error"))
    def test_general_error_handling(self, mock_file):
        """Test handling of general errors."""
        # Execute
        result = get_completion_results_by_type("AAPL", DocumentType.MDA)

        # Verify
        assert result == {}