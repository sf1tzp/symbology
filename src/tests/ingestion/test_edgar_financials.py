import pytest
import pandas as pd
from datetime import datetime
from unittest.mock import patch, MagicMock

from src.python.database.crud_company import create_company
from src.python.database.crud_filing import create_filing
from src.python.database.models import Company, Filing
from src.python.ingestion.edgar import (
    store_balance_sheet_data,
    store_income_statement_data,
    get_balance_sheet_values,
    get_income_statement_values
)


class TestEdgarFinancials:
    """Tests for Edgar financial data extraction and storage."""
    
    @pytest.fixture
    def test_company(self, db_session, sample_company_data):
        """Create a test company."""
        company = create_company(sample_company_data, session=db_session)
        return company

    @pytest.fixture
    def test_filing(self, db_session, test_company, sample_filing_data):
        """Create a test filing."""
        filing_data = sample_filing_data.copy()
        filing_data["company_id"] = test_company.id
        filing = create_filing(filing_data, session=db_session)
        return filing
    
    @pytest.fixture
    def mock_balance_sheet_df(self):
        """Create a mock balance sheet dataframe."""
        data = {
            'concept': [
                'us-gaap_Assets',
                'us-gaap_Liabilities',
                'us-gaap_StockholdersEquity'
            ],
            'label': [
                'Total Assets',
                'Total Liabilities',
                'Total Stockholders\' Equity'
            ],
            '2022-12-31': [
                1000000000.0,
                600000000.0,
                400000000.0
            ]
        }
        return pd.DataFrame(data)
    
    @pytest.fixture
    def mock_income_statement_df(self):
        """Create a mock income statement dataframe."""
        data = {
            'concept': [
                'us-gaap_RevenueFromContractWithCustomer',
                'us-gaap_CostOfGoodsAndServicesSold',
                'us-gaap_GrossProfit',
                'us-gaap_NetIncomeLoss'
            ],
            'label': [
                'Revenue',
                'Cost of Revenue',
                'Gross Profit',
                'Net Income'
            ],
            '2022-12-31': [
                500000000.0,
                -300000000.0,
                200000000.0,
                100000000.0
            ]
        }
        return pd.DataFrame(data)
    
    @patch('src.python.ingestion.edgar.get_balance_sheet_values')
    def test_store_balance_sheet_data(self, mock_get_values, db_session, test_company, test_filing, mock_balance_sheet_df):
        """Test storing balance sheet data from an EDGAR filing."""
        # Mock the get_balance_sheet_values function to return our test dataframe
        mock_get_values.return_value = mock_balance_sheet_df
        
        # Create a mock EDGAR filing object
        mock_edgar_filing = MagicMock()
        mock_edgar_filing.period_of_report = '2022-12-31'
        
        # Call the function
        results = store_balance_sheet_data(
            edgar_filing=mock_edgar_filing,
            db_company=test_company,
            db_filing=test_filing,
            session=db_session
        )
        
        # Verify the mock was called correctly
        mock_get_values.assert_called_once_with(mock_edgar_filing)
        
        # Check results
        assert results["total_concepts"] == 3
        assert results["total_values"] == 3
        assert "2022-12-31" in results["dates"]
        
        # Check that all the expected concepts are in the results
        assert "us-gaap_Assets" in results["concepts"]
        assert "us-gaap_Liabilities" in results["concepts"]
        assert "us-gaap_StockholdersEquity" in results["concepts"]
        
        # Verify that the labels were stored correctly
        assert results["concepts"]["us-gaap_Assets"] == "Total Assets"
    
    @patch('src.python.ingestion.edgar.get_income_statement_values')
    def test_store_income_statement_data(self, mock_get_values, db_session, test_company, test_filing, mock_income_statement_df):
        """Test storing income statement data from an EDGAR filing."""
        # Mock the get_income_statement_values function to return our test dataframe
        mock_get_values.return_value = mock_income_statement_df
        
        # Create a mock EDGAR filing object
        mock_edgar_filing = MagicMock()
        mock_edgar_filing.period_of_report = '2022-12-31'
        
        # Call the function
        results = store_income_statement_data(
            edgar_filing=mock_edgar_filing,
            db_company=test_company,
            db_filing=test_filing,
            session=db_session
        )
        
        # Verify the mock was called correctly
        mock_get_values.assert_called_once_with(mock_edgar_filing)
        
        # Check results
        assert results["total_concepts"] == 4
        assert results["total_values"] == 4
        assert "2022-12-31" in results["dates"]
        
        # Check that all the expected concepts are in the results
        assert "us-gaap_RevenueFromContractWithCustomer" in results["concepts"]
        assert "us-gaap_NetIncomeLoss" in results["concepts"]
        
        # Verify that the labels were stored correctly
        assert results["concepts"]["us-gaap_NetIncomeLoss"] == "Net Income"
        
    @patch('src.python.ingestion.edgar.XBRL.from_filing')
    def test_get_balance_sheet_values(self, mock_xbrl, db_session):
        """Test extracting balance sheet values from a filing."""
        # Create mock objects
        mock_filing = MagicMock()
        mock_filing.period_of_report = '2022-12-31'
        
        mock_xbrl_instance = MagicMock()
        mock_balance_sheet = MagicMock()
        
        # Set up the chain of mock returns
        mock_xbrl.return_value = mock_xbrl_instance
        mock_xbrl_instance.statements.balance_sheet.return_value = mock_balance_sheet
        mock_balance_sheet.to_dataframe.return_value = pd.DataFrame({
            'concept': ['us-gaap_Assets'],
            'label': ['Total Assets'],
            'is_abstract': [False],
            'has_values': [True],
            'level': [0],
            '2022-12-31': [1000000000.0]
        })
        
        # Call the function
        result_df = get_balance_sheet_values(mock_filing)
        
        # Verify the mock was called correctly
        mock_xbrl.assert_called_once_with(mock_filing)
        mock_xbrl_instance.statements.balance_sheet.assert_called_once()
        mock_balance_sheet.to_dataframe.assert_called_once()
        
        # Check that the result dataframe has the expected columns
        assert 'concept' in result_df.columns
        assert 'label' in result_df.columns 
        assert '2022-12-31' in result_df.columns
        
        # Check that the filtered data is correct
        assert len(result_df) == 1
        assert result_df.iloc[0]['concept'] == 'us-gaap_Assets'
        assert result_df.iloc[0]['label'] == 'Total Assets'
        assert result_df.iloc[0]['2022-12-31'] == 1000000000.0
    
    @patch('src.python.ingestion.edgar.XBRL.from_filing')
    def test_get_income_statement_values(self, mock_xbrl, db_session):
        """Test extracting income statement values from a filing."""
        # Create mock objects
        mock_filing = MagicMock()
        mock_filing.period_of_report = '2022-12-31'
        
        mock_xbrl_instance = MagicMock()
        mock_income_statement = MagicMock()
        
        # Set up the chain of mock returns
        mock_xbrl.return_value = mock_xbrl_instance
        mock_xbrl_instance.statements.income_statement.return_value = mock_income_statement
        mock_income_statement.to_dataframe.return_value = pd.DataFrame({
            'concept': ['us-gaap_NetIncomeLoss'],
            'label': ['Net Income'],
            'abstract': [False],
            'level': [0],
            '2022-12-31': [100000000.0]
        })
        
        # Call the function
        result_df = get_income_statement_values(mock_filing)
        
        # Verify the mock was called correctly
        mock_xbrl.assert_called_once_with(mock_filing)
        mock_xbrl_instance.statements.income_statement.assert_called_once()
        mock_income_statement.to_dataframe.assert_called_once()
        
        # Check that the result dataframe has the expected columns
        assert 'concept' in result_df.columns
        assert 'label' in result_df.columns 
        assert '2022-12-31' in result_df.columns
        
        # Check that the filtered data is correct
        assert len(result_df) == 1
        assert result_df.iloc[0]['concept'] == 'us-gaap_NetIncomeLoss'
        assert result_df.iloc[0]['label'] == 'Net Income'
        assert result_df.iloc[0]['2022-12-31'] == 100000000.0