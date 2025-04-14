import pytest
from datetime import datetime, timedelta
import pandas as pd
from sqlalchemy.exc import IntegrityError

# Use absolute imports for test files
from src.python.financial_processing import (
    process_balance_sheet_dataframe,
    process_income_statement_dataframe,
    process_cash_flow_statement_dataframe,
    store_balance_sheet_data,
    store_income_statement_data,
    store_cash_flow_statement_data
)
from src.python.database.crud_company import create_company
from src.python.database.crud_filing import create_filing
from src.python.database.crud_financials import (
    get_or_create_financial_concept,
    store_balance_sheet_value,
    store_income_statement_value,
    store_cash_flow_statement_value,
    get_balance_sheet_values_by_company,
    get_income_statement_values_by_company,
    get_cash_flow_statement_values_by_company,
    get_balance_sheet_by_date,
    get_income_statement_by_date,
    get_cash_flow_statement_by_date,
    get_all_concepts,
)
from src.python.database.models import (
    FinancialConcept,
    BalanceSheetValue,
    IncomeStatementValue,
    CashFlowStatementValue,
    Company,
    Filing
)


class TestFinancialData:
    """Test cases for financial data models and CRUD operations."""

    @pytest.fixture
    def test_company(self, db_session, sample_company_data):
        """Create a test company for financial data tests."""
        company = create_company(sample_company_data, session=db_session)
        return company

    @pytest.fixture
    def test_filing(self, db_session, test_company, sample_filing_data):
        """Create a test filing for financial data tests."""
        filing_data = sample_filing_data.copy()
        filing_data["company_id"] = test_company.id
        filing = create_filing(filing_data, session=db_session)
        return filing

    @pytest.fixture
    def test_concept(self, db_session, sample_financial_concept_data):
        """Create a test financial concept."""
        concept = get_or_create_financial_concept(
            concept_id=sample_financial_concept_data["concept_id"],
            label=sample_financial_concept_data["labels"][0],
            session=db_session
        )
        return concept

    @pytest.fixture
    def sample_cash_flow_statement_data(self):
        """Sample data for cash flow statement tests."""
        return {
            "value_date": datetime.strptime("2022-12-31", "%Y-%m-%d"),
            "value": 10500000.0
        }

    @pytest.fixture
    def sample_cash_flow_statement_df(self):
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

    def test_create_financial_concept(self, db_session, sample_financial_concept_data):
        """Test creating a new financial concept."""
        # Create a concept
        concept = get_or_create_financial_concept(
            concept_id=sample_financial_concept_data["concept_id"],
            label=sample_financial_concept_data["labels"][0],
            session=db_session
        )

        # Verify concept was created
        assert concept.id is not None
        assert concept.concept_id == sample_financial_concept_data["concept_id"]
        assert concept.labels == [sample_financial_concept_data["labels"][0]]

        # Test retrieving the same concept adds new label
        concept = get_or_create_financial_concept(
            concept_id=sample_financial_concept_data["concept_id"],
            label="Alternative Label",
            session=db_session
        )

        # Verify label was added
        assert len(concept.labels) == 2
        assert "Alternative Label" in concept.labels

    def test_store_balance_sheet_value(self, db_session, test_company, test_filing, test_concept, sample_balance_sheet_data):
        """Test storing a balance sheet value."""
        # Create balance sheet value
        bs_value = store_balance_sheet_value(
            company_id=test_company.id,
            filing_id=test_filing.id,
            concept_id=test_concept.id,
            value_date=sample_balance_sheet_data["value_date"],
            value=sample_balance_sheet_data["value"],
            session=db_session
        )

        # Verify value was created
        assert bs_value.id is not None
        assert bs_value.company_id == test_company.id
        assert bs_value.filing_id == test_filing.id
        assert bs_value.concept_id == test_concept.id
        assert bs_value.value == sample_balance_sheet_data["value"]

        # Test updating an existing value
        updated_bs_value = store_balance_sheet_value(
            company_id=test_company.id,
            filing_id=test_filing.id,
            concept_id=test_concept.id,
            value_date=sample_balance_sheet_data["value_date"],
            value=999999999.0,  # Different value
            session=db_session
        )

        # Verify the value was updated (same ID but different value)
        assert updated_bs_value.id == bs_value.id
        assert updated_bs_value.value == 999999999.0

    def test_store_income_statement_value(self, db_session, test_company, test_filing, test_concept, sample_income_statement_data):
        """Test storing an income statement value."""
        # Create income statement value
        is_value = store_income_statement_value(
            company_id=test_company.id,
            filing_id=test_filing.id,
            concept_id=test_concept.id,
            value_date=sample_income_statement_data["value_date"],
            value=sample_income_statement_data["value"],
            session=db_session
        )

        # Verify value was created
        assert is_value.id is not None
        assert is_value.company_id == test_company.id
        assert is_value.filing_id == test_filing.id
        assert is_value.concept_id == test_concept.id
        assert is_value.value == sample_income_statement_data["value"]

        # Test updating an existing value
        updated_is_value = store_income_statement_value(
            company_id=test_company.id,
            filing_id=test_filing.id,
            concept_id=test_concept.id,
            value_date=sample_income_statement_data["value_date"],
            value=200000000.0,  # Different value
            session=db_session
        )

        # Verify the value was updated (same ID but different value)
        assert updated_is_value.id == is_value.id
        assert updated_is_value.value == 200000000.0

    def test_store_cash_flow_statement_value(self, db_session, test_company, test_filing, test_concept, sample_cash_flow_statement_data):
        """Test storing a cash flow statement value."""
        # Create cash flow statement value
        cf_value = store_cash_flow_statement_value(
            company_id=test_company.id,
            filing_id=test_filing.id,
            concept_id=test_concept.id,
            value_date=sample_cash_flow_statement_data["value_date"],
            value=sample_cash_flow_statement_data["value"],
            session=db_session
        )

        # Verify value was created
        assert cf_value.id is not None
        assert cf_value.company_id == test_company.id
        assert cf_value.filing_id == test_filing.id
        assert cf_value.concept_id == test_concept.id
        assert cf_value.value == sample_cash_flow_statement_data["value"]

        # Test updating an existing value
        updated_cf_value = store_cash_flow_statement_value(
            company_id=test_company.id,
            filing_id=test_filing.id,
            concept_id=test_concept.id,
            value_date=sample_cash_flow_statement_data["value_date"],
            value=50000000.0,  # Different value
            session=db_session
        )

        # Verify the value was updated (same ID but different value)
        assert updated_cf_value.id == cf_value.id
        assert updated_cf_value.value == 50000000.0

    def test_process_balance_sheet_dataframe(self, db_session, test_company, test_filing, sample_balance_sheet_df):
        """Test processing a balance sheet dataframe."""
        # Process the dataframe
        results = process_balance_sheet_dataframe(
            company_id=test_company.id,
            filing_id=test_filing.id,
            df=sample_balance_sheet_df,
            session=db_session
        )

        # Verify results
        assert results["total_concepts"] == 3  # Three concepts in the sample dataframe
        assert results["total_values"] == 3    # One value per concept
        assert "2022-12-31" in results["dates"]

        # Check that all concepts were created
        concepts = db_session.query(FinancialConcept).all()
        assert len(concepts) == 3

        # Check that all values were stored
        values = db_session.query(BalanceSheetValue).all()
        assert len(values) == 3

        # Check that concepts have correct labels
        cash_concept = db_session.query(FinancialConcept).filter(
            FinancialConcept.concept_id == "us-gaap_CashAndCashEquivalentsAtCarryingValue"
        ).first()
        assert "Cash and Cash Equivalents" in cash_concept.labels

        # Check that values are correctly stored
        cash_value = db_session.query(BalanceSheetValue).filter(
            BalanceSheetValue.concept_id == cash_concept.id
        ).first()
        assert cash_value.value == 13931000000.0

    def test_process_income_statement_dataframe(self, db_session, test_company, test_filing, sample_income_statement_df):
        """Test processing an income statement dataframe."""
        # Process the dataframe
        results = process_income_statement_dataframe(
            company_id=test_company.id,
            filing_id=test_filing.id,
            df=sample_income_statement_df,
            session=db_session
        )

        # Verify results
        assert results["total_concepts"] == 3  # Three concepts in the sample dataframe
        assert results["total_values"] == 3    # One value per concept
        assert "2022-12-31" in results["dates"]

        # Check that all concepts were created
        concepts = db_session.query(FinancialConcept).all()
        assert len(concepts) == 3

        # Check that all values were stored
        values = db_session.query(IncomeStatementValue).all()
        assert len(values) == 3

        # Check that concepts have correct labels
        revenue_concept = db_session.query(FinancialConcept).filter(
            FinancialConcept.concept_id == "us-gaap_RevenueFromContractWithCustomerExcludingAssessedTax"
        ).first()
        assert "Revenue" in revenue_concept.labels

        # Check that values are correctly stored
        revenue_value = db_session.query(IncomeStatementValue).filter(
            IncomeStatementValue.concept_id == revenue_concept.id
        ).first()
        assert revenue_value.value == 198270000000.0

    def test_process_cash_flow_statement_dataframe(self, db_session, test_company, test_filing, sample_cash_flow_statement_df):
        """Test processing a cash flow statement dataframe."""
        # Process the dataframe
        results = process_cash_flow_statement_dataframe(
            company_id=test_company.id,
            filing_id=test_filing.id,
            df=sample_cash_flow_statement_df,
            session=db_session
        )

        # Verify results
        assert results["total_concepts"] == 3  # Three concepts in the sample dataframe
        assert results["total_values"] == 3    # One value per concept
        assert "2022-12-31" in results["dates"]

        # Check that all concepts were created
        concepts = db_session.query(FinancialConcept).filter(
            FinancialConcept.concept_id.like("us-gaap_NetCash%")
        ).all()
        assert len(concepts) == 3

        # Check that all values were stored
        values = db_session.query(CashFlowStatementValue).all()
        assert len(values) == 3

        # Check that concepts have correct labels
        operating_cash_concept = db_session.query(FinancialConcept).filter(
            FinancialConcept.concept_id == "us-gaap_NetCashProvidedByUsedInOperatingActivities"
        ).first()
        assert "Net Cash Provided by Operating Activities" in operating_cash_concept.labels

        # Check that values are correctly stored
        operating_cash_value = db_session.query(CashFlowStatementValue).filter(
            CashFlowStatementValue.concept_id == operating_cash_concept.id
        ).first()
        assert operating_cash_value.value == 105000000.0

    def test_get_balance_sheet_values_by_company(self, db_session, test_company, test_filing, sample_balance_sheet_df):
        """Test retrieving balance sheet values by company."""
        # First, process the dataframe to create values
        process_balance_sheet_dataframe(
            company_id=test_company.id,
            filing_id=test_filing.id,
            df=sample_balance_sheet_df,
            session=db_session
        )

        # Get values for the company
        values = get_balance_sheet_values_by_company(test_company.id, session=db_session)

        # Verify we got all 3 values
        assert len(values) == 3

        # Check that values have concept information
        assert all("concept_name" in value for value in values)
        assert all("labels" in value for value in values)

        # Test with date filtering
        future_date = datetime.now() + timedelta(days=365)
        filtered_values = get_balance_sheet_values_by_company(
            test_company.id,
            date_start=future_date,
            session=db_session
        )
        # Should have no values after the future date
        assert len(filtered_values) == 0

    def test_get_income_statement_values_by_company(self, db_session, test_company, test_filing, sample_income_statement_df):
        """Test retrieving income statement values by company."""
        # First, process the dataframe to create values
        process_income_statement_dataframe(
            company_id=test_company.id,
            filing_id=test_filing.id,
            df=sample_income_statement_df,
            session=db_session
        )

        # Get values for the company
        values = get_income_statement_values_by_company(test_company.id, session=db_session)

        # Verify we got all 3 values
        assert len(values) == 3

        # Check that values have concept information
        assert all("concept_name" in value for value in values)
        assert all("labels" in value for value in values)

        # Test with date filtering
        future_date = datetime.now() + timedelta(days=365)
        filtered_values = get_income_statement_values_by_company(
            test_company.id,
            date_start=future_date,
            session=db_session
        )
        # Should have no values after the future date
        assert len(filtered_values) == 0

    def test_get_cash_flow_statement_values_by_company(self, db_session, test_company, test_filing, sample_cash_flow_statement_df):
        """Test retrieving cash flow statement values by company."""
        # First, process the dataframe to create values
        process_cash_flow_statement_dataframe(
            company_id=test_company.id,
            filing_id=test_filing.id,
            df=sample_cash_flow_statement_df,
            session=db_session
        )

        # Get values for the company
        values = get_cash_flow_statement_values_by_company(test_company.id, session=db_session)

        # Verify we got all 3 values
        assert len(values) == 3

        # Check that values have concept information
        assert all("concept_name" in value for value in values)
        assert all("labels" in value for value in values)

        # Test with date filtering
        future_date = datetime.now() + timedelta(days=365)
        filtered_values = get_cash_flow_statement_values_by_company(
            test_company.id,
            date_start=future_date,
            session=db_session
        )
        # Should have no values after the future date
        assert len(filtered_values) == 0

    def test_get_balance_sheet_by_date(self, db_session, test_company, test_filing, sample_balance_sheet_df):
        """Test retrieving a balance sheet for a specific date."""
        # First, process the dataframe to create values
        process_balance_sheet_dataframe(
            company_id=test_company.id,
            filing_id=test_filing.id,
            df=sample_balance_sheet_df,
            session=db_session
        )

        # Get balance sheet as of report date
        report_date = datetime.strptime("2022-12-31", "%Y-%m-%d")
        balance_sheet = get_balance_sheet_by_date(
            company_id=test_company.id,
            as_of_date=report_date,
            session=db_session
        )

        # Verify structure
        assert "company_id" in balance_sheet
        assert "concepts" in balance_sheet
        assert len(balance_sheet["concepts"]) == 3

        # Check specific concept
        cash_concept = "us-gaap_CashAndCashEquivalentsAtCarryingValue"
        assert cash_concept in balance_sheet["concepts"]
        assert balance_sheet["concepts"][cash_concept]["value"] == 13931000000.0

    def test_get_income_statement_by_date(self, db_session, test_company, test_filing, sample_income_statement_df):
        """Test retrieving an income statement for a specific date."""
        # First, process the dataframe to create values
        process_income_statement_dataframe(
            company_id=test_company.id,
            filing_id=test_filing.id,
            df=sample_income_statement_df,
            session=db_session
        )

        # Get income statement as of report date
        report_date = datetime.strptime("2022-12-31", "%Y-%m-%d")
        income_statement = get_income_statement_by_date(
            company_id=test_company.id,
            as_of_date=report_date,
            session=db_session
        )

        # Verify structure
        assert "company_id" in income_statement
        assert "concepts" in income_statement
        assert len(income_statement["concepts"]) == 3

        # Check specific concept
        revenue_concept = "us-gaap_RevenueFromContractWithCustomerExcludingAssessedTax"
        assert revenue_concept in income_statement["concepts"]
        assert income_statement["concepts"][revenue_concept]["value"] == 198270000000.0

    def test_get_cash_flow_statement_by_date(self, db_session, test_company, test_filing, sample_cash_flow_statement_df):
        """Test retrieving a cash flow statement for a specific date."""
        # First, process the dataframe to create values
        process_cash_flow_statement_dataframe(
            company_id=test_company.id,
            filing_id=test_filing.id,
            df=sample_cash_flow_statement_df,
            session=db_session
        )

        # Get cash flow statement as of report date
        report_date = datetime.strptime("2022-12-31", "%Y-%m-%d")
        cash_flow_statement = get_cash_flow_statement_by_date(
            company_id=test_company.id,
            as_of_date=report_date,
            session=db_session
        )

        # Verify structure
        assert "company_id" in cash_flow_statement
        assert "concepts" in cash_flow_statement
        assert len(cash_flow_statement["concepts"]) == 3

        # Check specific concept
        operating_cash_concept = "us-gaap_NetCashProvidedByUsedInOperatingActivities"
        assert operating_cash_concept in cash_flow_statement["concepts"]
        assert cash_flow_statement["concepts"][operating_cash_concept]["value"] == 105000000.0

    def test_get_all_concepts(self, db_session, test_company, test_filing, sample_balance_sheet_df):
        """Test retrieving all financial concepts."""
        # First, process the dataframe to create concepts
        process_balance_sheet_dataframe(
            company_id=test_company.id,
            filing_id=test_filing.id,
            df=sample_balance_sheet_df,
            session=db_session
        )

        # Get all concepts
        concepts = get_all_concepts(session=db_session)

        # Verify we got all 3 concepts
        assert len(concepts) == 3

        # Check that concepts have expected structure
        assert all(isinstance(concept["labels"], list) for concept in concepts)
        assert all("concept_id" in concept for concept in concepts)

    def test_company_balance_sheet_relationship(self, db_session, test_company, test_filing, test_concept, sample_balance_sheet_data):
        """Test the relationship between Company and BalanceSheetValue."""
        # Create a balance sheet value
        bs_value = store_balance_sheet_value(
            company_id=test_company.id,
            filing_id=test_filing.id,
            concept_id=test_concept.id,
            value_date=sample_balance_sheet_data["value_date"],
            value=sample_balance_sheet_data["value"],
            session=db_session
        )

        # Refresh company object
        db_session.refresh(test_company)

        # Verify company has balance sheet values
        assert hasattr(test_company, "balance_sheet_values")
        assert len(test_company.balance_sheet_values) == 1
        assert test_company.balance_sheet_values[0].id == bs_value.id

        # Verify value has company
        assert bs_value.company is not None
        assert bs_value.company.id == test_company.id

    def test_company_income_statement_relationship(self, db_session, test_company, test_filing, test_concept, sample_income_statement_data):
        """Test the relationship between Company and IncomeStatementValue."""
        # Create an income statement value
        is_value = store_income_statement_value(
            company_id=test_company.id,
            filing_id=test_filing.id,
            concept_id=test_concept.id,
            value_date=sample_income_statement_data["value_date"],
            value=sample_income_statement_data["value"],
            session=db_session
        )

        # Refresh company object
        db_session.refresh(test_company)

        # Verify company has income statement values
        assert hasattr(test_company, "income_statement_values")
        assert len(test_company.income_statement_values) == 1
        assert test_company.income_statement_values[0].id == is_value.id

        # Verify value has company
        assert is_value.company is not None
        assert is_value.company.id == test_company.id

    def test_company_cash_flow_statement_relationship(self, db_session, test_company, test_filing, test_concept, sample_cash_flow_statement_data):
        """Test the relationship between Company and CashFlowStatementValue."""
        # Create a cash flow statement value
        cf_value = store_cash_flow_statement_value(
            company_id=test_company.id,
            filing_id=test_filing.id,
            concept_id=test_concept.id,
            value_date=sample_cash_flow_statement_data["value_date"],
            value=sample_cash_flow_statement_data["value"],
            session=db_session
        )

        # Refresh company object
        db_session.refresh(test_company)

        # Verify company has cash flow statement values
        assert hasattr(test_company, "cash_flow_statement_values")
        assert len(test_company.cash_flow_statement_values) == 1
        assert test_company.cash_flow_statement_values[0].id == cf_value.id

        # Verify value has company
        assert cf_value.company is not None
        assert cf_value.company.id == test_company.id

    def test_filing_balance_sheet_relationship(self, db_session, test_company, test_filing, test_concept, sample_balance_sheet_data):
        """Test the relationship between Filing and BalanceSheetValue."""
        # Create a balance sheet value
        bs_value = store_balance_sheet_value(
            company_id=test_company.id,
            filing_id=test_filing.id,
            concept_id=test_concept.id,
            value_date=sample_balance_sheet_data["value_date"],
            value=sample_balance_sheet_data["value"],
            session=db_session
        )

        # Refresh filing object
        db_session.refresh(test_filing)

        # Verify filing has balance sheet values
        assert hasattr(test_filing, "balance_sheet_values")
        assert len(test_filing.balance_sheet_values) == 1
        assert test_filing.balance_sheet_values[0].id == bs_value.id

        # Verify value has filing
        assert bs_value.filing is not None
        assert bs_value.filing.id == test_filing.id

    def test_filing_income_statement_relationship(self, db_session, test_company, test_filing, test_concept, sample_income_statement_data):
        """Test the relationship between Filing and IncomeStatementValue."""
        # Create an income statement value
        is_value = store_income_statement_value(
            company_id=test_company.id,
            filing_id=test_filing.id,
            concept_id=test_concept.id,
            value_date=sample_income_statement_data["value_date"],
            value=sample_income_statement_data["value"],
            session=db_session
        )

        # Refresh filing object
        db_session.refresh(test_filing)

        # Verify filing has income statement values
        assert hasattr(test_filing, "income_statement_values")
        assert len(test_filing.income_statement_values) == 1
        assert test_filing.income_statement_values[0].id == is_value.id

        # Verify value has filing
        assert is_value.filing is not None
        assert is_value.filing.id == test_filing.id

    def test_filing_cash_flow_statement_relationship(self, db_session, test_company, test_filing, test_concept, sample_cash_flow_statement_data):
        """Test the relationship between Filing and CashFlowStatementValue."""
        # Create a cash flow statement value
        cf_value = store_cash_flow_statement_value(
            company_id=test_company.id,
            filing_id=test_filing.id,
            concept_id=test_concept.id,
            value_date=sample_cash_flow_statement_data["value_date"],
            value=sample_cash_flow_statement_data["value"],
            session=db_session
        )

        # Refresh filing object
        db_session.refresh(test_filing)

        # Verify filing has cash flow statement values
        assert hasattr(test_filing, "cash_flow_statement_values")
        assert len(test_filing.cash_flow_statement_values) == 1
        assert test_filing.cash_flow_statement_values[0].id == cf_value.id

        # Verify value has filing
        assert cf_value.filing is not None
        assert cf_value.filing.id == test_filing.id

    def test_concept_balance_sheet_relationship(self, db_session, test_company, test_filing, test_concept, sample_balance_sheet_data):
        """Test the relationship between FinancialConcept and BalanceSheetValue."""
        # Create a balance sheet value
        bs_value = store_balance_sheet_value(
            company_id=test_company.id,
            filing_id=test_filing.id,
            concept_id=test_concept.id,
            value_date=sample_balance_sheet_data["value_date"],
            value=sample_balance_sheet_data["value"],
            session=db_session
        )

        # Refresh concept object
        db_session.refresh(test_concept)

        # Verify concept has balance sheet values
        assert hasattr(test_concept, "balance_sheet_values")
        assert len(test_concept.balance_sheet_values) == 1
        assert test_concept.balance_sheet_values[0].id == bs_value.id

        # Verify value has concept
        assert bs_value.concept is not None
        assert bs_value.concept.id == test_concept.id

    def test_concept_income_statement_relationship(self, db_session, test_company, test_filing, test_concept, sample_income_statement_data):
        """Test the relationship between FinancialConcept and IncomeStatementValue."""
        # Create an income statement value
        is_value = store_income_statement_value(
            company_id=test_company.id,
            filing_id=test_filing.id,
            concept_id=test_concept.id,
            value_date=sample_income_statement_data["value_date"],
            value=sample_income_statement_data["value"],
            session=db_session
        )

        # Refresh concept object
        db_session.refresh(test_concept)

        # Verify concept has income statement values
        assert hasattr(test_concept, "income_statement_values")
        assert len(test_concept.income_statement_values) == 1
        assert test_concept.income_statement_values[0].id == is_value.id

        # Verify value has concept
        assert is_value.concept is not None
        assert is_value.concept.id == test_concept.id

    def test_concept_cash_flow_statement_relationship(self, db_session, test_company, test_filing, test_concept, sample_cash_flow_statement_data):
        """Test the relationship between FinancialConcept and CashFlowStatementValue."""
        # Create a cash flow statement value
        cf_value = store_cash_flow_statement_value(
            company_id=test_company.id,
            filing_id=test_filing.id,
            concept_id=test_concept.id,
            value_date=sample_cash_flow_statement_data["value_date"],
            value=sample_cash_flow_statement_data["value"],
            session=db_session
        )

        # Refresh concept object
        db_session.refresh(test_concept)

        # Verify concept has cash flow statement values
        assert hasattr(test_concept, "cash_flow_statement_values")
        assert len(test_concept.cash_flow_statement_values) == 1
        assert test_concept.cash_flow_statement_values[0].id == cf_value.id

        # Verify value has concept
        assert cf_value.concept is not None
        assert cf_value.concept.id == test_concept.id