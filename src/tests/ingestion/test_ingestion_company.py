from datetime import date
from unittest import mock

import pytest
from uuid_extensions import uuid7

from src.ingestion.ingestion_helpers import ingest_company


def test_ingest_company_happy_path():
    """Test the successful ingestion of company data."""
    # Setup mock company data from EDGAR
    mock_edgar_company = mock.MagicMock()
    mock_edgar_company.cik = '0001234567'
    mock_edgar_company.name = 'Test Company Inc.'
    mock_edgar_company.display_name = 'TEST COMPANY INC.'
    mock_edgar_company.is_company = True
    mock_edgar_company.tickers = ['TEST']
    mock_edgar_company.exchanges = ['NYSE']
    mock_edgar_company.sic = '7370'
    mock_edgar_company.sic_description = 'Technology Services'
    mock_edgar_company.entity_type = 'CORPORATION'
    mock_edgar_company.ein = '12-3456789'
    mock_edgar_company.former_names = [{'name': 'Old Test Inc.', 'date': '2020-01-01'}]
    mock_edgar_company.fiscal_year_end = '1231'  # MMDD format

    # Setup mock database return value
    mock_db_company = mock.MagicMock()
    mock_db_company.id = uuid7()

    with mock.patch('src.ingestion.ingestion_helpers.get_company', return_value=mock_edgar_company) as mock_get_company, \
         mock.patch('src.ingestion.ingestion_helpers.upsert_company_by_cik', return_value=mock_db_company) as mock_upsert_company, \
         mock.patch('src.ingestion.ingestion_helpers.logger') as mock_logger:

        # Call the function
        edgar_company, company_id = ingest_company('TEST')

        # Verify the company was fetched from EDGAR
        mock_get_company.assert_called_once_with('TEST')

        # Verify company data was properly transformed and stored in database
        mock_upsert_company.assert_called_once()
        company_data = mock_upsert_company.call_args[0][0]

        # Verify key data transformations
        assert company_data['cik'] == '0001234567'
        assert company_data['name'] == 'Test Company Inc.'
        assert isinstance(company_data['fiscal_year_end'], date)
        assert company_data['fiscal_year_end'].month == 12
        assert company_data['fiscal_year_end'].day == 31

        # Verify the function returns the expected values
        assert edgar_company == mock_edgar_company
        assert company_id == mock_db_company.id

        # Verify successful ingestion was logged
        mock_logger.info.assert_called_with(
            "company_ingested",
            ticker='TEST',
            cik='0001234567',
            company_id=str(mock_db_company.id)
        )


def test_ingest_company_invalid_fiscal_year_format():
    """Test handling invalid fiscal year end format."""
    mock_edgar_company = mock.MagicMock()
    mock_edgar_company.cik = '0001234567'
    mock_edgar_company.name = 'Test Company Inc.'
    mock_edgar_company.fiscal_year_end = 'invalid'  # Invalid format
    mock_edgar_company.tickers = ['TEST']
    mock_edgar_company.sic = '7370'
    mock_edgar_company.sic_description = 'Technology Services'
    mock_edgar_company.is_company = True

    mock_db_company = mock.MagicMock()
    mock_db_company.id = uuid7()

    with mock.patch('src.ingestion.ingestion_helpers.get_company', return_value=mock_edgar_company), \
         mock.patch('src.ingestion.ingestion_helpers.upsert_company_by_cik', return_value=mock_db_company) as mock_upsert_company, \
         mock.patch('src.ingestion.ingestion_helpers.logger') as mock_logger:

        edgar_company, company_id = ingest_company('TEST')

        # Check that a warning gets logged - don't check the specific message format
        # since it might have changed in the implementation
        mock_logger.warning.assert_called_once()
        args, kwargs = mock_logger.warning.call_args
        assert args[0] == "invalid_fiscal_year_end_format"
        assert kwargs['value'] == 'invalid'
        assert kwargs['cik'] == '0001234567'

        # Verify fiscal_year_end was set to None
        company_data = mock_upsert_company.call_args[0][0]
        assert company_data['fiscal_year_end'] is None


def test_ingest_company_missing_optional_fields():
    """Test company ingestion with missing optional fields."""
    mock_edgar_company = mock.MagicMock()
    mock_edgar_company.cik = '0001234567'
    mock_edgar_company.name = 'Test Company Inc.'
    mock_edgar_company.display_name = 'TEST COMPANY INC.'
    mock_edgar_company.is_company = True
    mock_edgar_company.tickers = ['TEST']
    mock_edgar_company.sic = '7370'
    mock_edgar_company.sic_description = 'Technology Services'
    # No entity_type, ein, former_names, fiscal_year_end attributes

    # Create a mock object that correctly handles hasattr checks
    # by ensuring that these attributes don't exist
    mock_edgar_company = mock.MagicMock(spec=[
        'cik', 'name', 'display_name', 'is_company',
        'tickers', 'sic', 'sic_description'
    ])
    mock_edgar_company.cik = '0001234567'
    mock_edgar_company.name = 'Test Company Inc.'
    mock_edgar_company.display_name = 'TEST COMPANY INC.'
    mock_edgar_company.is_company = True
    mock_edgar_company.tickers = ['TEST']
    mock_edgar_company.sic = '7370'
    mock_edgar_company.sic_description = 'Technology Services'

    mock_db_company = mock.MagicMock()
    mock_db_company.id = uuid7()

    with mock.patch('src.ingestion.ingestion_helpers.get_company', return_value=mock_edgar_company), \
         mock.patch('src.ingestion.ingestion_helpers.upsert_company_by_cik', return_value=mock_db_company) as mock_upsert_company:

        edgar_company, company_id = ingest_company('TEST')

        # Verify data handling for missing fields
        company_data = mock_upsert_company.call_args[0][0]
        assert company_data['exchanges'] == []
        assert company_data['entity_type'] is None
        assert company_data['ein'] is None
        assert company_data['former_names'] == []
        assert company_data['fiscal_year_end'] is None


def test_ingest_company_error_handling():
    """Test error handling in company ingestion."""
    with mock.patch('src.ingestion.ingestion_helpers.get_company',
                   side_effect=Exception("EDGAR API error")), \
         mock.patch('src.ingestion.ingestion_helpers.logger') as mock_logger:

        with pytest.raises(Exception) as excinfo:
            ingest_company('TEST')

        assert "EDGAR API error" in str(excinfo.value)
        mock_logger.error.assert_called_with(
            "ingest_company_failed",
            ticker='TEST',
            error="EDGAR API error",
            exc_info=True
        )

