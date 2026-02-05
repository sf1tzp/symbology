from datetime import date
from unittest import mock

import pytest
from collector.ingestion.ingestion_helpers import ingest_filings
from uuid_extensions import uuid7


def test_ingest_filing_happy_path():
    """Test the successful ingestion of filing data."""
    company_id = uuid7()
    mock_edgar_company = mock.MagicMock()
    mock_edgar_company.cik = '0001234567'

    # Mock 10-K filing data
    mock_filing = mock.MagicMock()
    mock_filing.accession_number = '0001234567-23-000123'
    mock_filing.form = '10-K'
    mock_filing.filing_date = date(2023, 3, 31)
    mock_filing.filing_url = 'https://example.com/filing.html'
    mock_filing.period_of_report = date(2022, 12, 31)

    # Mock database filing object
    mock_db_filing = mock.MagicMock()
    mock_db_filing.id = uuid7()

    with mock.patch('src.ingestion.ingestion_helpers.get_10k_filing', return_value=mock_filing) as mock_get_filing, \
         mock.patch('src.ingestion.ingestion_helpers.upsert_filing_by_accession_number', return_value=mock_db_filing) as mock_upsert_filing, \
         mock.patch('src.ingestion.ingestion_helpers.logger') as mock_logger, \
         mock.patch('src.ingestion.ingestion_helpers._year_from_period_of_report', return_value=2022) as _mock_get_year:

        # Call the function
        filing, filing_id = ingest_filings(company_id, mock_edgar_company, 2022)

        # Verify the filing was fetched from EDGAR
        mock_get_filing.assert_called_once_with(mock_edgar_company, 2022)

        # Verify filing data was properly stored in database
        mock_upsert_filing.assert_called_once()
        filing_data = mock_upsert_filing.call_args[0][0]
        assert filing_data['company_id'] == company_id
        assert filing_data['accession_number'] == '0001234567-23-000123'
        assert filing_data['filing_type'] == '10-K'
        assert filing_data['filing_date'] == date(2023, 3, 31)
        assert filing_data['filing_url'] == 'https://example.com/filing.html'
        assert filing_data['period_of_report'] == date(2022, 12, 31)

        # Verify the function returns the expected values
        assert filing == mock_filing
        assert filing_id == mock_db_filing.id

        # Verify successful ingestion was logged
        mock_logger.info.assert_called_with(
            "filing_ingested",
            company_id=str(company_id),
            accession_number='0001234567-23-000123',
            filing_id=str(mock_db_filing.id),
            year=2022
        )


def test_ingest_filing_not_found():
    """Test handling when a filing is not found for a given year."""
    company_id = uuid7()
    mock_edgar_company = mock.MagicMock()

    with mock.patch('src.ingestion.ingestion_helpers.get_10k_filing', return_value=None) as _mock_get_filing, \
         mock.patch('src.ingestion.ingestion_helpers.logger') as mock_logger:

        # Call the function
        filing, filing_id = ingest_filings(company_id, mock_edgar_company, 2022)

        # Verify the result when filing is not found
        assert filing is None
        assert filing_id is None

        # Verify warning was logged
        mock_logger.warning.assert_called_with(
            "no_filing_found",
            company_id=str(company_id),
            year=2022
        )


def test_ingest_filing_error_handling():
    """Test error handling in filing ingestion."""
    company_id = uuid7()
    mock_edgar_company = mock.MagicMock()

    with mock.patch('src.ingestion.ingestion_helpers.get_10k_filing',
                   side_effect=Exception("Filing retrieval error")), \
         mock.patch('src.ingestion.ingestion_helpers.logger') as mock_logger:

        with pytest.raises(Exception) as excinfo:
            ingest_filings(company_id, mock_edgar_company, 2022)

        assert "Filing retrieval error" in str(excinfo.value)
        mock_logger.error.assert_called_with(
            "ingest_filing_failed",
            company_id=str(company_id),
            year=2022,
            error="Filing retrieval error",
            exc_info=True
        )
