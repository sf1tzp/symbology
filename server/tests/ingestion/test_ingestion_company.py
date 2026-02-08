from datetime import date
from unittest import mock

import pytest
from symbology.ingestion.ingestion_helpers import ingest_company
from uuid_extensions import uuid7


def test_ingest_company_happy_path():
    """Test the successful ingestion of company data."""
    # Setup mock entity data (Company.data)
    mock_entity_data = mock.MagicMock()
    mock_entity_data.name = 'Test Company Inc.'
    mock_entity_data.display_name = 'TEST COMPANY INC.'
    mock_entity_data.sic = '7370'
    mock_entity_data.sic_description = 'Technology Services'
    mock_entity_data.former_names = [{'name': 'Old Test Inc.', 'date': '2020-01-01'}]

    # Setup mock EDGAR Company object
    mock_edgar_company = mock.MagicMock()
    mock_edgar_company.data = mock_entity_data
    mock_edgar_company.get_ticker.return_value = 'TEST'
    mock_edgar_company.get_exchanges.return_value = ['NYSE']
    mock_edgar_company.fiscal_year_end = '1231'  # MMDD format

    # Setup mock database return value
    mock_db_company = mock.MagicMock()
    mock_db_company.id = uuid7()

    with mock.patch('symbology.ingestion.ingestion_helpers.Company', return_value=mock_edgar_company), \
         mock.patch('symbology.ingestion.ingestion_helpers.get_company_by_ticker', return_value=None), \
         mock.patch('symbology.ingestion.ingestion_helpers.get_company_by_cik', return_value=None), \
         mock.patch('symbology.ingestion.ingestion_helpers.create_company', return_value=mock_db_company) as mock_create, \
         mock.patch('symbology.ingestion.ingestion_helpers.logger') as mock_logger:

        # Call the function
        edgar_company, company_id = ingest_company('TEST')

        # Verify company was created (not updated, since get_company_by_ticker returned None)
        mock_create.assert_called_once()
        company_data = mock_create.call_args[0][0]

        # Verify key data transformations
        assert company_data['name'] == 'Test Company Inc.'
        assert company_data['display_name'] == 'TEST COMPANY INC.'
        assert company_data['ticker'] == 'TEST'
        assert company_data['cik'] is not None
        assert company_data['exchanges'] == ['NYSE']
        assert company_data['sic'] == '7370'
        assert company_data['sic_description'] == 'Technology Services'
        assert company_data['former_names'] == [{'name': 'Old Test Inc.', 'date': '2020-01-01'}]
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
            company_id=str(mock_db_company.id)
        )


def test_ingest_company_invalid_fiscal_year_format():
    """Test handling invalid fiscal year end format."""
    mock_entity_data = mock.MagicMock()
    mock_entity_data.name = 'Test Company Inc.'
    mock_entity_data.display_name = 'TEST COMPANY INC.'
    mock_entity_data.sic = '7370'
    mock_entity_data.sic_description = 'Technology Services'
    mock_entity_data.former_names = []

    mock_edgar_company = mock.MagicMock()
    mock_edgar_company.data = mock_entity_data
    mock_edgar_company.get_ticker.return_value = 'TEST'
    mock_edgar_company.get_exchanges.return_value = ['NYSE']
    mock_edgar_company.fiscal_year_end = 'invalid'  # Invalid format

    mock_db_company = mock.MagicMock()
    mock_db_company.id = uuid7()

    with mock.patch('symbology.ingestion.ingestion_helpers.Company', return_value=mock_edgar_company), \
         mock.patch('symbology.ingestion.ingestion_helpers.get_company_by_ticker', return_value=None), \
         mock.patch('symbology.ingestion.ingestion_helpers.get_company_by_cik', return_value=None), \
         mock.patch('symbology.ingestion.ingestion_helpers.create_company', return_value=mock_db_company) as mock_create, \
         mock.patch('symbology.ingestion.ingestion_helpers.logger') as mock_logger:

        edgar_company, company_id = ingest_company('TEST')

        # Check that a warning gets logged
        mock_logger.warning.assert_called_once()
        args, kwargs = mock_logger.warning.call_args
        assert args[0] == "invalid_fiscal_year_end_format"
        assert kwargs['value'] == 'invalid'
        assert kwargs['ticker'] == 'TEST'

        # Verify fiscal_year_end was set to None
        company_data = mock_create.call_args[0][0]
        assert company_data['fiscal_year_end'] is None


def test_ingest_company_missing_optional_fields():
    """Test company ingestion with missing optional fields."""
    # Create entity_data with spec that omits optional attrs
    mock_entity_data = mock.MagicMock(spec=[
        'name', 'display_name', 'sic', 'sic_description'
    ])
    mock_entity_data.name = 'Test Company Inc.'
    mock_entity_data.display_name = 'TEST COMPANY INC.'
    mock_entity_data.sic = '7370'
    mock_entity_data.sic_description = 'Technology Services'

    mock_edgar_company = mock.MagicMock()
    mock_edgar_company.data = mock_entity_data
    mock_edgar_company.get_ticker.return_value = 'TEST'
    mock_edgar_company.get_exchanges.return_value = []
    mock_edgar_company.fiscal_year_end = None

    mock_db_company = mock.MagicMock()
    mock_db_company.id = uuid7()

    with mock.patch('symbology.ingestion.ingestion_helpers.Company', return_value=mock_edgar_company), \
         mock.patch('symbology.ingestion.ingestion_helpers.get_company_by_ticker', return_value=None), \
         mock.patch('symbology.ingestion.ingestion_helpers.get_company_by_cik', return_value=None), \
         mock.patch('symbology.ingestion.ingestion_helpers.create_company', return_value=mock_db_company) as mock_create:

        edgar_company, company_id = ingest_company('TEST')

        # Verify data handling for missing fields
        company_data = mock_create.call_args[0][0]
        assert company_data['former_names'] == []
        assert company_data['fiscal_year_end'] is None


def test_ingest_company_error_handling():
    """Test error handling in company ingestion."""
    with mock.patch('symbology.ingestion.ingestion_helpers.Company',
                   side_effect=Exception("EDGAR API error")), \
         mock.patch('symbology.ingestion.ingestion_helpers.logger') as mock_logger:

        with pytest.raises(Exception) as excinfo:
            ingest_company('TEST')

        assert "EDGAR API error" in str(excinfo.value)
        mock_logger.error.assert_called_with(
            "ingest_company_failed",
            ticker='TEST',
            error="EDGAR API error",
            exc_info=True
        )
