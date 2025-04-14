import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from datetime import datetime

from src.ingestion.ten_k import process_10k_filing, batch_process_10k_filings


class TestTenK:
    """Test cases for 10-K processing functions."""

    @pytest.fixture
    def mock_edgar_company(self):
        """Mock EDGAR company data."""
        company = MagicMock()
        company.cik = "0000320193"
        company.name = "Test Company Inc."
        company.tickers = ["TEST"]
        company.exchanges = ["NYSE"]
        company.sic = "7370"
        company.sic_description = "SERVICES-COMPUTER PROGRAMMING, DATA PROCESSING, ETC."
        company.fiscal_year_end = "0930"
        company.entity_type = "CORPORATE"
        return company

    @pytest.fixture
    def mock_edgar_filing(self):
        """Mock EDGAR filing data."""
        filing = MagicMock()
        filing.accession_number = "0000320193-23-000010"
        filing.filing_date = datetime(2023, 1, 15)
        filing.period_of_report = "2022-12-31"
        filing.form = "10-K"
        filing.file_number = "001-12345"
        filing.film_number = "231234567"
        filing.link = "https://www.sec.gov/Archives/edgar/data/320193/000032019323000010/test-20221231.htm"
        return filing

    @pytest.fixture
    def mock_financial_data(self):
        """Mock financial statement data."""
        # Balance Sheet
        balance_sheet = pd.DataFrame({
            'concept': ['Assets', 'Liabilities', 'Equity'],
            'value': [1000000, 500000, 500000],
            'period_end': ['2022-12-31', '2022-12-31', '2022-12-31']
        })

        # Income Statement
        income_statement = pd.DataFrame({
            'concept': ['Revenue', 'Expenses', 'NetIncome'],
            'value': [2000000, 1500000, 500000],
            'period_end': ['2022-12-31', '2022-12-31', '2022-12-31']
        })

        # Cash Flow
        cash_flow = pd.DataFrame({
            'concept': ['OperatingCashFlow', 'InvestingCashFlow', 'FinancingCashFlow'],
            'value': [600000, -300000, -100000],
            'period_end': ['2022-12-31', '2022-12-31', '2022-12-31']
        })

        # Cover Page
        cover_page = pd.DataFrame({
            'concept': ['DocumentType', 'DocumentPeriodEndDate', 'EntityRegistrantName'],
            'value': ['10-K', '2022-12-31', 'Test Company Inc.'],
            'period_end': ['2022-12-31', '2022-12-31', '2022-12-31']
        })

        return {
            'balance_sheet': balance_sheet,
            'income_statement': income_statement,
            'cash_flow': cash_flow,
            'cover_page': cover_page
        }

    @patch('src.ingestion.ten_k.edgar_login')
    @patch('src.ingestion.ten_k.get_company')
    @patch('src.ingestion.ten_k.get_10k_filing')
    @patch('src.ingestion.ten_k.get_filing_by_accession_number')
    @patch('src.ingestion.ten_k.upsert_company')
    @patch('src.ingestion.ten_k.create_filing')
    @patch('src.ingestion.ten_k.get_balance_sheet_values')
    @patch('src.ingestion.ten_k.store_balance_sheet_data')
    @patch('src.ingestion.ten_k.get_income_statement_values')
    @patch('src.ingestion.ten_k.store_income_statement_data')
    @patch('src.ingestion.ten_k.get_cash_flow_statement_values')
    @patch('src.ingestion.ten_k.store_cash_flow_statement_data')
    @patch('src.ingestion.ten_k.get_cover_page_values')
    @patch('src.ingestion.ten_k.store_cover_page_data')
    @patch('src.ingestion.ten_k.get_business_description')
    @patch('src.ingestion.ten_k.create_source_document')
    @patch('src.ingestion.ten_k.get_risk_factors')
    @patch('src.ingestion.ten_k.get_management_discussion')
    @patch('src.ingestion.ten_k.get_db_session')
    def test_process_10k_filing_success(
        self,
        mock_get_session,
        mock_get_management_discussion,
        mock_get_risk_factors,
        mock_create_source_document,
        mock_get_business_description,
        mock_store_cover_page_data,
        mock_get_cover_page_values,
        mock_store_cash_flow_statement_data,
        mock_get_cash_flow_statement_values,
        mock_store_income_statement_data,
        mock_get_income_statement_values,
        mock_store_balance_sheet_data,
        mock_get_balance_sheet_values,
        mock_create_filing,
        mock_upsert_company,
        mock_get_filing_by_accession_number,
        mock_get_10k_filing,
        mock_get_company,
        mock_edgar_login,
        mock_edgar_company,
        mock_edgar_filing,
        mock_financial_data,
        db_session
    ):
        """Test successful processing of a 10-K filing."""
        # Configure the session mock
        mock_get_session.return_value = db_session

        # Configure mocks
        mock_edgar_login.return_value = None
        mock_get_company.return_value = mock_edgar_company
        mock_get_10k_filing.return_value = mock_edgar_filing
        mock_get_filing_by_accession_number.return_value = None  # Filing doesn't exist yet

        mock_db_company = MagicMock()
        mock_db_company.id = 1
        mock_upsert_company.return_value = mock_db_company

        mock_db_filing = MagicMock()
        mock_db_filing.id = 1
        mock_create_filing.return_value = mock_db_filing

        # Financial data mocks
        mock_get_balance_sheet_values.return_value = mock_financial_data['balance_sheet']
        mock_store_balance_sheet_data.return_value = None
        mock_get_income_statement_values.return_value = mock_financial_data['income_statement']
        mock_store_income_statement_data.return_value = None
        mock_get_cash_flow_statement_values.return_value = mock_financial_data['cash_flow']
        mock_store_cash_flow_statement_data.return_value = None
        mock_get_cover_page_values.return_value = mock_financial_data['cover_page']
        mock_store_cover_page_data.return_value = None

        # Textual data mocks
        mock_get_business_description.return_value = "Business Description Text"
        mock_get_risk_factors.return_value = "Risk Factors Text"
        mock_get_management_discussion.return_value = "Management Discussion Text"

        # Source document creation mock
        mock_create_source_document.return_value = None

        # Call the function
        result = process_10k_filing("TEST", 2022, "test@example.com")

        # Assertions
        assert result["success"] == True
        assert result["ticker"] == "TEST"
        assert result["year"] == 2022
        assert result["company_id"] == 1
        assert result["filing_id"] == 1

        # Verify that all the mocked functions were called
        mock_edgar_login.assert_called_once()
        mock_get_company.assert_called_once_with("TEST")
        mock_get_10k_filing.assert_called_once_with(mock_edgar_company, 2022)
        mock_get_filing_by_accession_number.assert_called_once()
        mock_upsert_company.assert_called_once()
        mock_create_filing.assert_called_once()
        mock_get_balance_sheet_values.assert_called_once()
        mock_store_balance_sheet_data.assert_called_once()
        mock_get_income_statement_values.assert_called_once()
        mock_store_income_statement_data.assert_called_once()
        mock_get_cash_flow_statement_values.assert_called_once()
        mock_store_cash_flow_statement_data.assert_called_once()
        mock_get_cover_page_values.assert_called_once()
        mock_store_cover_page_data.assert_called_once()
        mock_get_business_description.assert_called_once()
        mock_get_risk_factors.assert_called_once()
        mock_get_management_discussion.assert_called_once()
        # We expect create_source_document to be called at least 3 times (for business, risk, and management)
        assert mock_create_source_document.call_count >= 3

    @patch('src.ingestion.ten_k.edgar_login')
    @patch('src.ingestion.ten_k.get_company')
    @patch('src.ingestion.ten_k.get_db_session')
    def test_process_10k_filing_company_not_found(
        self,
        mock_get_session,
        mock_get_company,
        mock_login,
        db_session
    ):
        """Test handling when company is not found in EDGAR."""
        # Configure the session mock
        mock_get_session.return_value = db_session

        # Configure mocks
        mock_login.return_value = None
        mock_get_company.return_value = None

        # Call the function
        result = process_10k_filing("NOTFOUND", 2022, "test@example.com")

        # Assertions
        assert result["success"] == False
        assert result["ticker"] == "NOTFOUND"
        assert result["year"] == 2022
        assert "Could not find company" in result["message"]

        # Verify mock calls
        mock_login.assert_called_once()
        mock_get_company.assert_called_once_with("NOTFOUND")

    @patch('src.ingestion.ten_k.process_10k_filing')
    def test_batch_process_10k_filings(self, mock_process, db_session):
        """Test batch processing of multiple 10-K filings."""
        # For tickers=[AAPL, MSFT] and years=[2022, 2021], we need 4 responses
        # The function will call process_10k_filing for each combination
        mock_process.side_effect = [
            {"success": True, "ticker": "AAPL", "year": 2022},  # AAPL, 2022
            {"success": True, "ticker": "AAPL", "year": 2021},  # AAPL, 2021
            {"success": False, "ticker": "MSFT", "year": 2022, "message": "Error"},  # MSFT, 2022
            {"success": True, "ticker": "MSFT", "year": 2021},  # MSFT, 2021
        ]

        # Call the function
        results = batch_process_10k_filings(
            tickers=["AAPL", "MSFT"],
            years=[2022, 2021],
            edgar_contact="test@example.com"
        )

        # Assertions
        assert len(results) == 4
        assert results[0]["success"] == True
        assert results[0]["ticker"] == "AAPL"
        assert results[0]["year"] == 2022
        assert results[1]["success"] == True
        assert results[1]["ticker"] == "AAPL"
        assert results[1]["year"] == 2021
        assert results[2]["success"] == False
        assert results[2]["ticker"] == "MSFT"
        assert results[2]["year"] == 2022
        assert results[3]["success"] == True
        assert results[3]["ticker"] == "MSFT"
        assert results[3]["year"] == 2021

        # Verify mock calls - 4 calls expected (2 tickers × 2 years)
        assert mock_process.call_count == 4

        # Define the expected call arguments (without the tuple nesting)
        expected_args = [
            ("AAPL", 2022, "test@example.com"),
            ("AAPL", 2021, "test@example.com"),
            ("MSFT", 2022, "test@example.com"),
            ("MSFT", 2021, "test@example.com"),
        ]

        # Check that each call was made with the expected arguments
        for i, expected in enumerate(expected_args):
            call_args = mock_process.call_args_list[i][0]
            assert call_args == expected
