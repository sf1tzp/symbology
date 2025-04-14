"""
Tests for income statement operations.
"""
import pytest
from datetime import datetime, timedelta
import pandas as pd

from src.ingestion.database.crud_income_statement import (
    store_income_statement_value,
    get_income_statement_values_by_company,
    get_income_statement_by_date
)
from src.ingestion.financial_processing import process_income_statement_dataframe
from src.ingestion.database.models import (
    FinancialConcept,
    IncomeStatementValue
)

# Import shared fixtures
pytest.importorskip("src.tests.db.fixtures_financials")
from src.tests.db.fixtures_financials import (
    test_company,
    test_filing,
    test_concept
)

class TestIncomeStatement:
    """Test cases for income statement operations."""

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