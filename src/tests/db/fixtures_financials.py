"""
Shared fixtures for financial data tests.
"""
import pytest
from datetime import datetime
import pandas as pd

from src.python.database.crud_company import create_company
from src.python.database.crud_filing import create_filing
from src.python.database.crud_financial_concepts import get_or_create_financial_concept


@pytest.fixture
def test_company(db_session, sample_company_data):
    """Create a test company for financial data tests."""
    company = create_company(sample_company_data, session=db_session)
    return company


@pytest.fixture
def test_filing(db_session, test_company, sample_filing_data):
    """Create a test filing for financial data tests."""
    filing_data = sample_filing_data.copy()
    filing_data["company_id"] = test_company.id
    filing = create_filing(filing_data, session=db_session)
    return filing


@pytest.fixture
def test_concept(db_session, sample_financial_concept_data):
    """Create a test financial concept."""
    concept = get_or_create_financial_concept(
        concept_id=sample_financial_concept_data["concept_id"],
        label=sample_financial_concept_data["labels"][0],
        session=db_session
    )
    return concept


@pytest.fixture
def sample_cash_flow_statement_data():
    """Sample data for cash flow statement tests."""
    return {
        "value_date": datetime.strptime("2022-12-31", "%Y-%m-%d"),
        "value": 10500000.0
    }


@pytest.fixture
def sample_cover_page_data():
    """Sample data for cover page tests."""
    return {
        "value_date": datetime.strptime("2022-12-31", "%Y-%m-%d"),
        "value": 0.0  # Cover page often has text or numeric identifiers
    }


@pytest.fixture
def sample_cash_flow_statement_df():
    """Create a sample cash flow statement dataframe for testing."""
    data = {
        'concept': [
            'us-gaap_NetCashProvidedByUsedInOperatingActivities',
            'us-gaap_NetCashProvidedByUsedInInvestingActivities',
            'us-gaap_NetCashProvidedByUsedInFinancingActivities'
        ],
        'label': [
            'Net Cash Provided by Operating Activities',
            'Net Cash Used in Investing Activities',
            'Net Cash Used in Financing Activities'
        ],
        '2022-12-31': [
            105000000.0,
            -87000000.0,
            -5000000.0
        ]
    }
    return pd.DataFrame(data)


@pytest.fixture
def sample_cover_page_df():
    """Create a sample cover page dataframe for testing."""
    data = {
        'concept': [
            'dei_EntityRegistrantName',
            'dei_EntityCommonStockSharesOutstanding',
            'dei_DocumentType'
        ],
        'label': [
            'Entity Registrant Name',
            'Entity Common Stock, Shares Outstanding',
            'Document Type'
        ],
        '2022-12-31': [
            "",
            100.0,
            ""
        ]
    }
    return pd.DataFrame(data)