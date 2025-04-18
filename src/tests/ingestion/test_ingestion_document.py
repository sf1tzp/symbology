from datetime import date
from unittest import mock

import pytest
from uuid_extensions import uuid7

from src.ingestion.ingestion_helpers import ingest_filing_documents


def test_ingest_filing_documents_happy_path():
    """Test the successful ingestion of filing documents."""
    company_id = uuid7()
    filing_id = uuid7()
    company_name = "Test Company Inc."

    mock_filing = mock.MagicMock()
    mock_filing.form = '10-K'
    mock_filing.filing_date = date(2023, 3, 31)

    # Mock document sections from filing
    with mock.patch('src.ingestion.ingestion_helpers.get_business_description', return_value="Business description text") as mock_get_business, \
         mock.patch('src.ingestion.ingestion_helpers.get_risk_factors', return_value="Risk factors text") as mock_get_risks, \
         mock.patch('src.ingestion.ingestion_helpers.get_management_discussion', return_value="MD&A text") as mock_get_mda, \
         mock.patch('src.ingestion.ingestion_helpers.find_or_create_document') as mock_create_document:

        # Configure document creation mock
        business_doc = mock.MagicMock()
        business_doc.id = uuid7()
        risk_doc = mock.MagicMock()
        risk_doc.id = uuid7()
        mda_doc = mock.MagicMock()
        mda_doc.id = uuid7()

        mock_create_document.side_effect = [business_doc, risk_doc, mda_doc]

        # Call the function
        document_uuids = ingest_filing_documents(company_id, filing_id, mock_filing, company_name)

        # Verify document content was extracted
        mock_get_business.assert_called_once_with(mock_filing)
        mock_get_risks.assert_called_once_with(mock_filing)
        mock_get_mda.assert_called_once_with(mock_filing)

        # Verify document creation calls
        assert mock_create_document.call_count == 3

        # Verify document names were formatted correctly
        assert mock_create_document.call_args_list[0][1]['document_name'] == "Test Company Inc. 10-K 2023-03-31 - Business Description"
        assert mock_create_document.call_args_list[1][1]['document_name'] == "Test Company Inc. 10-K 2023-03-31 - Risk Factors"
        assert mock_create_document.call_args_list[2][1]['document_name'] == "Test Company Inc. 10-K 2023-03-31 - Management Discussion"

        # Verify document content was stored correctly
        assert mock_create_document.call_args_list[0][1]['content'] == "Business description text"
        assert mock_create_document.call_args_list[1][1]['content'] == "Risk factors text"
        assert mock_create_document.call_args_list[2][1]['content'] == "MD&A text"

        # Verify document UUIDs were returned correctly
        assert document_uuids == {
            'business_description': business_doc.id,
            'risk_factors': risk_doc.id,
            'management_discussion': mda_doc.id
        }


def test_ingest_filing_documents_missing_sections():
    """Test document ingestion with missing document sections."""
    company_id = uuid7()
    filing_id = uuid7()

    mock_filing = mock.MagicMock()
    mock_filing.form = '10-K'
    mock_filing.filing_date = date(2023, 3, 31)

    # Only business description available, other sections missing
    with mock.patch('src.ingestion.ingestion_helpers.get_business_description', return_value="Business description text"), \
         mock.patch('src.ingestion.ingestion_helpers.get_risk_factors', return_value=None), \
         mock.patch('src.ingestion.ingestion_helpers.get_management_discussion', return_value=None), \
         mock.patch('src.ingestion.ingestion_helpers.find_or_create_document') as mock_create_document:

        business_doc = mock.MagicMock()
        business_doc.id = uuid7()
        mock_create_document.return_value = business_doc

        # Call the function
        document_uuids = ingest_filing_documents(company_id, filing_id, mock_filing)

        # Verify document creation was only called for business description
        assert mock_create_document.call_count == 1

        # Verify returned UUIDs only include business description
        assert 'business_description' in document_uuids
        assert 'risk_factors' not in document_uuids
        assert 'management_discussion' not in document_uuids


def test_ingest_filing_documents_default_company_name():
    """Test document ingestion with default company name."""
    company_id = uuid7()
    filing_id = uuid7()

    mock_filing = mock.MagicMock()
    mock_filing.form = '10-K'
    mock_filing.filing_date = date(2023, 3, 31)

    with mock.patch('src.ingestion.ingestion_helpers.get_business_description', return_value="Business description text"), \
         mock.patch('src.ingestion.ingestion_helpers.get_risk_factors', return_value=None), \
         mock.patch('src.ingestion.ingestion_helpers.get_management_discussion', return_value=None), \
         mock.patch('src.ingestion.ingestion_helpers.find_or_create_document') as mock_create_document:

        # No company_name provided - should default to "Company"
        ingest_filing_documents(company_id, filing_id, mock_filing)

        # Verify document name uses default company name
        assert mock_create_document.call_args[1]['document_name'] == "Company 10-K 2023-03-31 - Business Description"


def test_ingest_filing_documents_error_handling():
    """Test error handling in document ingestion."""
    company_id = uuid7()
    filing_id = uuid7()

    mock_filing = mock.MagicMock()

    with mock.patch('src.ingestion.ingestion_helpers.get_business_description',
                   side_effect=Exception("Document extraction failed")), \
         mock.patch('src.ingestion.ingestion_helpers.logger') as mock_logger:

        with pytest.raises(Exception) as excinfo:
            ingest_filing_documents(company_id, filing_id, mock_filing)

        assert "Document extraction failed" in str(excinfo.value)
        mock_logger.error.assert_called_with(
            "ingest_filing_documents_failed",
            company_id=str(company_id),
            filing_id=str(filing_id),
            error="Document extraction failed",
            exc_info=True
        )