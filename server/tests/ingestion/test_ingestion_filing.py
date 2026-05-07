from datetime import date
from unittest import mock

import pytest
from symbology.ingestion.ingestion_helpers import ingest_filings
from uuid_extensions import uuid7


def test_ingest_filing_happy_path():
    """Test the successful ingestion of filing data."""
    db_id = uuid7()

    # Mock 10-K filing data
    mock_filing = mock.MagicMock()
    mock_filing.accession_number = '0001234567-23-000123'
    mock_filing.form = '10-K'
    mock_filing.filing_date = date(2023, 3, 31)
    mock_filing.period_of_report = date(2022, 12, 31)
    mock_filing.url = 'https://example.com/filing.html'

    # Mock Company and its filings chain
    mock_company = mock.MagicMock()
    mock_company.get_filings.return_value.latest.return_value = mock_filing

    # Mock database filing object
    mock_db_filing = mock.MagicMock()
    mock_db_filing.id = uuid7()

    with mock.patch('symbology.ingestion.ingestion_helpers.Company', return_value=mock_company), \
         mock.patch('symbology.ingestion.ingestion_helpers.upsert_filing_by_accession_number', return_value=mock_db_filing) as mock_upsert_filing, \
         mock.patch('symbology.ingestion.ingestion_helpers.logger') as mock_logger:

        # Call with include_documents=False to avoid needing document mocks
        result = ingest_filings(db_id, 'TEST', '10-K', 1, include_documents=False)

        # Verify result is a list of tuples
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0] == ('TEST', '10-K', date(2022, 12, 31), mock_db_filing.id)

        # Verify filing data was properly stored in database
        mock_upsert_filing.assert_called_once()
        filing_data = mock_upsert_filing.call_args[0][0]
        assert filing_data['company_id'] == db_id
        assert filing_data['accession_number'] == '0001234567-23-000123'
        assert filing_data['form'] == '10-K'
        assert filing_data['filing_date'] == date(2023, 3, 31)
        assert filing_data['period_of_report'] == date(2022, 12, 31)
        assert filing_data['url'] == 'https://example.com/filing.html'

        # Verify successful ingestion was logged
        mock_logger.info.assert_any_call(
            "filing_ingested",
            company_id=str(db_id),
            accession_number='0001234567-23-000123',
            filing_id=str(mock_db_filing.id)
        )


def test_ingest_filing_not_found():
    """Test handling when no filings are found."""
    db_id = uuid7()

    # Mock Company so .get_filings().latest() returns None
    mock_company = mock.MagicMock()
    mock_company.get_filings.return_value.latest.return_value = None

    with mock.patch('symbology.ingestion.ingestion_helpers.Company', return_value=mock_company), \
         mock.patch('symbology.ingestion.ingestion_helpers.logger'):

        result = ingest_filings(db_id, 'TEST', '10-K', 1, include_documents=False)

        # When latest() returns None for count=1, filings list is empty
        assert result == []


def test_ingest_filing_error_handling():
    """Test error handling in filing ingestion."""
    db_id = uuid7()

    with mock.patch('symbology.ingestion.ingestion_helpers.Company',
                   side_effect=Exception("Filing retrieval error")), \
         mock.patch('symbology.ingestion.ingestion_helpers.logger') as mock_logger:

        with pytest.raises(Exception) as excinfo:
            ingest_filings(db_id, 'TEST', '10-K', 1)

        assert "Filing retrieval error" in str(excinfo.value)
        mock_logger.error.assert_called_with(
            "ingest_filing_failed",
            company_id=str(db_id),
            error="Filing retrieval error",
            exc_info=True
        )
