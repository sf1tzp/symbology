from unittest import mock

import pytest
from symbology.database.documents import DocumentType
from symbology.ingestion.ingestion_helpers import ingest_filing_documents
from uuid_extensions import uuid7


def test_ingest_filing_documents_happy_path():
    """Test the successful ingestion of filing documents."""
    company_id = uuid7()
    filing_id = uuid7()

    mock_filing = mock.MagicMock()
    mock_filing.form = '10-K'
    mock_filing.period_of_report = '2023-12-31'

    # Mock get_company returning a company with .name
    mock_company = mock.MagicMock()
    mock_company.name = 'Test Company Inc.'

    # Mock get_sections_for_document_types returning section content
    sections = {
        DocumentType.DESCRIPTION: "Business description text",
        DocumentType.RISK_FACTORS: "Risk factors text",
        DocumentType.MDA: "MD&A text",
    }

    with mock.patch('symbology.ingestion.ingestion_helpers.get_company', return_value=mock_company), \
         mock.patch('symbology.ingestion.ingestion_helpers.get_sections_for_document_types', return_value=sections), \
         mock.patch('symbology.ingestion.ingestion_helpers.find_or_create_document') as mock_create_document, \
         mock.patch('symbology.ingestion.ingestion_helpers.logger'):

        # Configure document creation mock
        business_doc = mock.MagicMock()
        business_doc.id = uuid7()
        risk_doc = mock.MagicMock()
        risk_doc.id = uuid7()
        mda_doc = mock.MagicMock()
        mda_doc.id = uuid7()

        mock_create_document.side_effect = [business_doc, risk_doc, mda_doc]

        # Call the function
        document_uuids = ingest_filing_documents(company_id, filing_id, mock_filing)

        # Verify document creation calls
        assert mock_create_document.call_count == 3

        # Verify document names use period_of_report (not filing_date)
        call_kwargs_list = [call[1] for call in mock_create_document.call_args_list]
        titles = [kw['title'] for kw in call_kwargs_list]
        assert "Test Company Inc. 10-K 2023-12-31 - Business Description" in titles
        assert "Test Company Inc. 10-K 2023-12-31 - Risk Factors" in titles
        assert "Test Company Inc. 10-K 2023-12-31 - Management Discussion and Analysis" in titles

        # Verify document content was stored correctly
        contents = [kw['content'] for kw in call_kwargs_list]
        assert "Business description text" in contents
        assert "Risk factors text" in contents
        assert "MD&A text" in contents

        # Verify document UUIDs were returned correctly
        assert document_uuids == {
            DocumentType.DESCRIPTION: business_doc.id,
            DocumentType.RISK_FACTORS: risk_doc.id,
            DocumentType.MDA: mda_doc.id
        }


def test_ingest_filing_documents_missing_sections():
    """Test document ingestion with missing document sections."""
    company_id = uuid7()
    filing_id = uuid7()

    mock_filing = mock.MagicMock()
    mock_filing.form = '10-K'
    mock_filing.period_of_report = '2023-12-31'

    mock_company = mock.MagicMock()
    mock_company.name = 'Test Company Inc.'

    # Only business description available
    sections = {
        DocumentType.DESCRIPTION: "Business description text",
    }

    with mock.patch('symbology.ingestion.ingestion_helpers.get_company', return_value=mock_company), \
         mock.patch('symbology.ingestion.ingestion_helpers.get_sections_for_document_types', return_value=sections), \
         mock.patch('symbology.ingestion.ingestion_helpers.find_or_create_document') as mock_create_document, \
         mock.patch('symbology.ingestion.ingestion_helpers.logger'):

        business_doc = mock.MagicMock()
        business_doc.id = uuid7()
        mock_create_document.return_value = business_doc

        document_uuids = ingest_filing_documents(company_id, filing_id, mock_filing)

        # Verify document creation was only called for business description
        assert mock_create_document.call_count == 1

        # Verify returned UUIDs only include business description
        assert DocumentType.DESCRIPTION in document_uuids
        assert DocumentType.RISK_FACTORS not in document_uuids
        assert DocumentType.MDA not in document_uuids


def test_ingest_filing_documents_uses_company_from_db():
    """Test that document ingestion uses company name from database, not parameter."""
    company_id = uuid7()
    filing_id = uuid7()

    mock_filing = mock.MagicMock()
    mock_filing.form = '10-K'
    mock_filing.period_of_report = '2023-12-31'

    # The impl always calls get_company(company_id) and uses company.name
    mock_company = mock.MagicMock()
    mock_company.name = 'DB Company Name'

    sections = {
        DocumentType.DESCRIPTION: "Business description text",
    }

    with mock.patch('symbology.ingestion.ingestion_helpers.get_company', return_value=mock_company) as mock_get_company, \
         mock.patch('symbology.ingestion.ingestion_helpers.get_sections_for_document_types', return_value=sections), \
         mock.patch('symbology.ingestion.ingestion_helpers.find_or_create_document') as mock_create_document, \
         mock.patch('symbology.ingestion.ingestion_helpers.logger'):

        mock_doc = mock.MagicMock()
        mock_doc.id = uuid7()
        mock_create_document.return_value = mock_doc

        # Pass a different company_name param — it should be ignored
        ingest_filing_documents(company_id, filing_id, mock_filing, company_name="Ignored Name")

        # Verify get_company was called with company_id
        mock_get_company.assert_called_once_with(company_id)

        # Verify document name uses the DB company name
        assert mock_create_document.call_args[1]['title'] == "DB Company Name 10-K 2023-12-31 - Business Description"


def test_ingest_filing_documents_error_handling():
    """Test error handling in document ingestion."""
    company_id = uuid7()
    filing_id = uuid7()

    mock_filing = mock.MagicMock()

    with mock.patch('symbology.ingestion.ingestion_helpers.get_company',
                   side_effect=Exception("Document extraction failed")), \
         mock.patch('symbology.ingestion.ingestion_helpers.logger') as mock_logger:

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
