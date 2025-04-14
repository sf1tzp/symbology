"""
Tests for cash flow statement operations.
"""
import pytest
from datetime import datetime, timedelta
import pandas as pd

from src.python.database.crud_cash_flow import (
    store_cash_flow_statement_value,
    get_cash_flow_statement_values_by_company,
    get_cash_flow_statement_by_date
)
from src.python.financial_processing import process_cash_flow_statement_dataframe
from src.python.database.models import (
    FinancialConcept,
    CashFlowStatementValue
)

# Import shared fixtures
pytest.importorskip("src.tests.db.fixtures_financials")
from src.tests.db.fixtures_financials import (
    test_company,
    test_filing,
    test_concept,
    sample_cash_flow_statement_data,
    sample_cash_flow_statement_df
)

class TestCashFlowStatement:
    """Test cases for cash flow statement operations."""

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