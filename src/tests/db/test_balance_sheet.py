"""
Tests for balance sheet operations.
"""
import pytest
from datetime import datetime, timedelta
import pandas as pd

from src.python.database.crud_balance_sheet import (
    store_balance_sheet_value,
    get_balance_sheet_values_by_company,
    get_balance_sheet_by_date
)
from src.python.financial_processing import process_balance_sheet_dataframe
from src.python.database.models import (
    FinancialConcept,
    BalanceSheetValue
)

# Import shared fixtures
pytest.importorskip("src.tests.db.fixtures_financials")
from src.tests.db.fixtures_financials import (
    test_company,
    test_filing,
    test_concept
)

class TestBalanceSheet:
    """Test cases for balance sheet operations."""

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