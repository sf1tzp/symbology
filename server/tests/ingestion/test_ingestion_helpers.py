from datetime import date
from unittest import mock

import pandas as pd
import pytest
from symbology.ingestion.ingestion_helpers import ingest_financial_data
from uuid_extensions import uuid7


def test_ingest_financial_data_happy_path():
    # Setup mocks
    company_id = uuid7()
    filing_id = uuid7()
    mock_filing = mock.MagicMock()
    mock_filing.period_of_report = date(2023, 12, 31)

    # Create sample dataframes for each statement type
    balance_sheet_df = pd.DataFrame({
        'concept': ['Assets', 'Liabilities'],
        'label': ['Total Assets', 'Total Liabilities'],
        '2023-12-31': [1000000, 500000]
    })

    income_stmt_df = pd.DataFrame({
        'concept': ['Revenue', 'NetIncome'],
        'label': ['Total Revenue', 'Net Income'],
        '2023-12-31': [2000000, 300000]
    })

    cash_flow_df = pd.DataFrame({
        'concept': ['OperatingCashFlow', 'InvestingCashFlow'],
        'label': ['Cash from Operations', 'Cash from Investing'],
        '2023-12-31': [400000, -100000]
    })

    cover_page_df = pd.DataFrame({
        'concept': ['SharesOutstanding'],
        'label': ['Shares Outstanding'],
        '2023-12-31': [1000000]
    })

    # Configure mocks
    with mock.patch('symbology.ingestion.ingestion_helpers.get_xbrl_for_filing', return_value=mock.MagicMock()), \
         mock.patch('symbology.ingestion.ingestion_helpers.get_balance_sheet_values', return_value=balance_sheet_df), \
         mock.patch('symbology.ingestion.ingestion_helpers.get_income_statement_values', return_value=income_stmt_df), \
         mock.patch('symbology.ingestion.ingestion_helpers.get_cash_flow_statement_values', return_value=cash_flow_df), \
         mock.patch('symbology.ingestion.ingestion_helpers.get_cover_page_values', return_value=cover_page_df), \
         mock.patch('symbology.ingestion.ingestion_helpers.find_or_create_financial_concept') as mock_create_concept, \
         mock.patch('symbology.ingestion.ingestion_helpers.upsert_financial_value') as mock_upsert_value:

        # Configure concept creation mock
        mock_concept = mock.MagicMock()
        mock_concept.id = uuid7()
        mock_create_concept.return_value = mock_concept

        # Call the function
        result = ingest_financial_data(company_id, filing_id, mock_filing)

        # Assertions
        assert result == {'balance_sheet': 2, 'income_statement': 2, 'cash_flow': 2, 'cover_page': 1}

        # Check concept creation calls
        assert mock_create_concept.call_count == 7  # Total number of financial concepts

        # Check value storage calls for numeric values
        assert mock_upsert_value.call_count == 7  # All numeric values


def test_ingest_financial_data_with_string_report_date():
    """Test handling of string period_of_report."""
    company_id = uuid7()
    filing_id = uuid7()
    mock_filing = mock.MagicMock()
    mock_filing.period_of_report = '2023-12-31'  # String date format

    balance_sheet_df = pd.DataFrame({
        'concept': ['Assets'],
        'label': ['Total Assets'],
        '2023-12-31': [1000000]
    })

    with mock.patch('symbology.ingestion.ingestion_helpers.get_xbrl_for_filing', return_value=mock.MagicMock()), \
         mock.patch('symbology.ingestion.ingestion_helpers.get_balance_sheet_values', return_value=balance_sheet_df), \
         mock.patch('symbology.ingestion.ingestion_helpers.get_income_statement_values', return_value=pd.DataFrame()), \
         mock.patch('symbology.ingestion.ingestion_helpers.get_cash_flow_statement_values', return_value=pd.DataFrame()), \
         mock.patch('symbology.ingestion.ingestion_helpers.get_cover_page_values', return_value=pd.DataFrame()), \
         mock.patch('symbology.ingestion.ingestion_helpers.find_or_create_financial_concept') as mock_create_concept, \
         mock.patch('symbology.ingestion.ingestion_helpers.upsert_financial_value') as mock_upsert_value:

        mock_concept = mock.MagicMock()
        mock_concept.id = uuid7()
        mock_create_concept.return_value = mock_concept

        result = ingest_financial_data(company_id, filing_id, mock_filing)

        assert result == {'balance_sheet': 1, 'income_statement': 0, 'cash_flow': 0, 'cover_page': 0}
        mock_upsert_value.assert_called_once()
        # Verify the date was properly converted from string to date object
        _, kwargs = mock_upsert_value.call_args
        assert kwargs['value_date'] == date(2023, 12, 31)


def test_ingest_financial_data_skips_missing_values():
    """Test handling of rows with missing values for the report date."""
    company_id = uuid7()
    filing_id = uuid7()
    mock_filing = mock.MagicMock()
    mock_filing.period_of_report = date(2023, 12, 31)

    # DataFrame with missing value for the report date
    balance_sheet_df = pd.DataFrame({
        'concept': ['Assets', 'Liabilities'],
        'label': ['Total Assets', 'Total Liabilities'],
        # Missing entry for '2023-12-31' in the second row
        '2023-12-31': [1000000, None]
    })

    with mock.patch('symbology.ingestion.ingestion_helpers.get_xbrl_for_filing', return_value=mock.MagicMock()), \
         mock.patch('symbology.ingestion.ingestion_helpers.get_balance_sheet_values', return_value=balance_sheet_df), \
         mock.patch('symbology.ingestion.ingestion_helpers.get_income_statement_values', return_value=pd.DataFrame()), \
         mock.patch('symbology.ingestion.ingestion_helpers.get_cash_flow_statement_values', return_value=pd.DataFrame()), \
         mock.patch('symbology.ingestion.ingestion_helpers.get_cover_page_values', return_value=pd.DataFrame()), \
         mock.patch('symbology.ingestion.ingestion_helpers.find_or_create_financial_concept') as mock_create_concept, \
         mock.patch('symbology.ingestion.ingestion_helpers.upsert_financial_value') as mock_upsert_value:

        mock_concept = mock.MagicMock()
        mock_concept.id = uuid7()
        mock_create_concept.return_value = mock_concept

        result = ingest_financial_data(company_id, filing_id, mock_filing)

        assert result == {'balance_sheet': 1, 'income_statement': 0, 'cash_flow': 0, 'cover_page': 0}
        assert mock_upsert_value.call_count == 1  # Only one valid value


def test_ingest_financial_data_handles_invalid_numeric_values():
    """Test handling of invalid numeric values."""
    company_id = uuid7()
    filing_id = uuid7()
    mock_filing = mock.MagicMock()
    mock_filing.period_of_report = date(2023, 12, 31)

    # DataFrame with invalid numeric value
    income_stmt_df = pd.DataFrame({
        'concept': ['Revenue'],
        'label': ['Total Revenue'],
        '2023-12-31': ['not-a-number']  # Invalid numeric value
    })

    with mock.patch('symbology.ingestion.ingestion_helpers.get_xbrl_for_filing', return_value=mock.MagicMock()), \
         mock.patch('symbology.ingestion.ingestion_helpers.get_balance_sheet_values', return_value=pd.DataFrame()), \
         mock.patch('symbology.ingestion.ingestion_helpers.get_income_statement_values', return_value=income_stmt_df), \
         mock.patch('symbology.ingestion.ingestion_helpers.get_cash_flow_statement_values', return_value=pd.DataFrame()), \
         mock.patch('symbology.ingestion.ingestion_helpers.get_cover_page_values', return_value=pd.DataFrame()), \
         mock.patch('symbology.ingestion.ingestion_helpers.find_or_create_financial_concept') as mock_create_concept, \
         mock.patch('symbology.ingestion.ingestion_helpers.upsert_financial_value') as mock_upsert_value, \
         mock.patch('symbology.ingestion.ingestion_helpers.logger') as mock_logger:

        mock_concept = mock.MagicMock()
        mock_concept.id = uuid7()
        mock_create_concept.return_value = mock_concept

        result = ingest_financial_data(company_id, filing_id, mock_filing)

        assert result == {'balance_sheet': 0, 'income_statement': 0, 'cash_flow': 0, 'cover_page': 0}
        assert mock_upsert_value.call_count == 0  # No valid values to insert
        # Check that a warning was logged
        mock_logger.warning.assert_called_with(
            "invalid_income_statement_value",
            concept='Revenue',
            value='not-a-number'
        )


def test_ingest_financial_data_builds_xbrl_once():
    """XBRL is built once and the same object is passed to all four statement getters."""
    company_id = uuid7()
    filing_id = uuid7()
    mock_filing = mock.MagicMock()
    mock_filing.period_of_report = date(2023, 12, 31)

    sentinel_xbrl = mock.MagicMock(name="xbrl")

    with mock.patch('symbology.ingestion.ingestion_helpers.get_xbrl_for_filing', return_value=sentinel_xbrl) as m_xbrl, \
         mock.patch('symbology.ingestion.ingestion_helpers.get_balance_sheet_values', return_value=pd.DataFrame()) as m_bs, \
         mock.patch('symbology.ingestion.ingestion_helpers.get_income_statement_values', return_value=pd.DataFrame()) as m_is, \
         mock.patch('symbology.ingestion.ingestion_helpers.get_cash_flow_statement_values', return_value=pd.DataFrame()) as m_cf, \
         mock.patch('symbology.ingestion.ingestion_helpers.get_cover_page_values', return_value=pd.DataFrame()) as m_cp, \
         mock.patch('symbology.ingestion.ingestion_helpers.find_or_create_financial_concept'), \
         mock.patch('symbology.ingestion.ingestion_helpers.upsert_financial_value'):

        ingest_financial_data(company_id, filing_id, mock_filing)

        # Built exactly once...
        m_xbrl.assert_called_once_with(mock_filing)
        # ...and threaded into every statement getter (no rebuilds).
        for getter in (m_bs, m_is, m_cf, m_cp):
            getter.assert_called_once()
            assert getter.call_args.kwargs.get('xbrl') is sentinel_xbrl


def test_ingest_financial_data_no_xbrl_returns_zero_counts():
    """A filing with no XBRL data yields zero counts and skips the statement getters."""
    company_id = uuid7()
    filing_id = uuid7()
    mock_filing = mock.MagicMock()

    with mock.patch('symbology.ingestion.ingestion_helpers.get_xbrl_for_filing', return_value=None), \
         mock.patch('symbology.ingestion.ingestion_helpers.get_balance_sheet_values') as m_bs:

        result = ingest_financial_data(company_id, filing_id, mock_filing)

    assert result == {'balance_sheet': 0, 'income_statement': 0, 'cash_flow': 0, 'cover_page': 0}
    m_bs.assert_not_called()


def test_ingest_financial_data_error_handling():
    """Test error handling when extraction fails."""
    company_id = uuid7()
    filing_id = uuid7()
    mock_filing = mock.MagicMock()

    with mock.patch('symbology.ingestion.ingestion_helpers.get_xbrl_for_filing', return_value=mock.MagicMock()), \
         mock.patch('symbology.ingestion.ingestion_helpers.get_balance_sheet_values',
                   side_effect=Exception("Failed to extract data")), \
         mock.patch('symbology.ingestion.ingestion_helpers.logger') as mock_logger:

        with pytest.raises(Exception) as excinfo:
            ingest_financial_data(company_id, filing_id, mock_filing)

        assert "Failed to extract data" in str(excinfo.value)
        mock_logger.error.assert_called_with(
            "ingest_financial_data_failed",
            company_id=str(company_id),
            filing_id=str(filing_id),
            error="Failed to extract data",
            exc_info=True
        )

