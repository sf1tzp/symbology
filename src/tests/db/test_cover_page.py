"""
Tests for cover page operations.
"""
import pytest
from datetime import datetime, timedelta
import pandas as pd

from src.ingestion.database.crud_cover_page import (
    store_cover_page_value,
    get_cover_page_values_by_company,
    get_cover_page_by_date
)
from src.ingestion.financial_processing import process_cover_page_dataframe
from src.ingestion.database.models import (
    FinancialConcept,
    CoverPageValue
)

# Import shared fixtures
pytest.importorskip("src.tests.db.fixtures_financials")
from src.tests.db.fixtures_financials import (
    test_company,
    test_filing,
    test_concept,
    sample_cover_page_data,
    sample_cover_page_df
)

class TestCoverPage:
    """Test cases for cover page operations."""

    def test_store_cover_page_value(self, db_session, test_company, test_filing, test_concept, sample_cover_page_data):
        """Test storing a cover page value."""
        # Create cover page value
        cp_value = store_cover_page_value(
            company_id=test_company.id,
            filing_id=test_filing.id,
            concept_id=test_concept.id,
            value_date=sample_cover_page_data["value_date"],
            value=sample_cover_page_data["value"],
            session=db_session
        )

        # Verify value was created
        assert cp_value.id is not None
        assert cp_value.company_id == test_company.id
        assert cp_value.filing_id == test_filing.id
        assert cp_value.concept_id == test_concept.id
        assert cp_value.value == sample_cover_page_data["value"]

        # Test updating an existing value
        updated_cp_value = store_cover_page_value(
            company_id=test_company.id,
            filing_id=test_filing.id,
            concept_id=test_concept.id,
            value_date=sample_cover_page_data["value_date"],
            value=1.0,  # Different value
            session=db_session
        )

        # Verify the value was updated (same ID but different value)
        assert updated_cp_value.id == cp_value.id
        assert updated_cp_value.value == 1.0

    def test_process_cover_page_dataframe(self, db_session, test_company, test_filing, sample_cover_page_df):
        """Test processing a cover page dataframe."""
        # Process the dataframe
        results = process_cover_page_dataframe(
            company_id=test_company.id,
            filing_id=test_filing.id,
            df=sample_cover_page_df,
            session=db_session
        )

        # Verify results
        assert results["total_concepts"] == 1  # One concept in the sample dataframe that has a value
        assert results["total_values"] == 1    # One value per concept
        assert "2022-12-31" in results["dates"]

        # Check that all concepts were created
        concepts = db_session.query(FinancialConcept).filter(
            FinancialConcept.concept_id.like("dei_%")
        ).all()
        assert len(concepts) == 1

        # Check that all values were stored
        values = db_session.query(CoverPageValue).all()
        assert len(values) == 1

        # Check that concepts have correct labels
        entity_shares_concept = db_session.query(FinancialConcept).filter(
            FinancialConcept.concept_id == "dei_EntityCommonStockSharesOutstanding"
        ).first()
        assert "Entity Common Stock, Shares Outstanding" in entity_shares_concept.labels

    def test_get_cover_page_values_by_company(self, db_session, test_company, test_filing, test_concept, sample_cover_page_data):
        """Test retrieving cover page values by company."""
        # Create a cover page value first
        cp_value = store_cover_page_value(
            company_id=test_company.id,
            filing_id=test_filing.id,
            concept_id=test_concept.id,
            value_date=sample_cover_page_data["value_date"],
            value=sample_cover_page_data["value"],
            session=db_session
        )

        # Get values for the company
        values = get_cover_page_values_by_company(test_company.id, session=db_session)

        # Verify we got the value
        assert len(values) == 1
        assert values[0]["company_id"] == test_company.id
        assert values[0]["concept_id"] == test_concept.id

        # Check that values have concept information
        assert "concept_name" in values[0]
        assert "labels" in values[0]

        # Test with date filtering
        future_date = datetime.now() + timedelta(days=365)
        filtered_values = get_cover_page_values_by_company(
            test_company.id,
            date_start=future_date,
            session=db_session
        )
        # Should have no values after the future date
        assert len(filtered_values) == 0

    def test_get_cover_page_by_date(self, db_session, test_company, test_filing, test_concept, sample_cover_page_data):
        """Test retrieving a cover page for a specific date."""
        # Create a cover page value first
        cp_value = store_cover_page_value(
            company_id=test_company.id,
            filing_id=test_filing.id,
            concept_id=test_concept.id,
            value_date=sample_cover_page_data["value_date"],
            value=sample_cover_page_data["value"],
            session=db_session
        )

        # Get cover page as of the value date
        cover_page = get_cover_page_by_date(
            company_id=test_company.id,
            as_of_date=sample_cover_page_data["value_date"],
            session=db_session
        )

        # Verify structure
        assert "company_id" in cover_page
        assert "concepts" in cover_page

        # Check specific concept - using test_concept.concept_id to get the actual concept ID
        concept_id = test_concept.concept_id
        assert concept_id in cover_page["concepts"]
        assert cover_page["concepts"][concept_id]["value"] == sample_cover_page_data["value"]

    def test_company_cover_page_relationship(self, db_session, test_company, test_filing, test_concept, sample_cover_page_data):
        """Test the relationship between Company and CoverPageValue."""
        # Create a cover page value
        cp_value = store_cover_page_value(
            company_id=test_company.id,
            filing_id=test_filing.id,
            concept_id=test_concept.id,
            value_date=sample_cover_page_data["value_date"],
            value=sample_cover_page_data["value"],
            session=db_session
        )

        # Refresh company object
        db_session.refresh(test_company)

        # Verify company has cover page values
        assert hasattr(test_company, "cover_page_values")
        assert len(test_company.cover_page_values) == 1
        assert test_company.cover_page_values[0].id == cp_value.id

        # Verify value has company
        assert cp_value.company is not None
        assert cp_value.company.id == test_company.id

    def test_filing_cover_page_relationship(self, db_session, test_company, test_filing, test_concept, sample_cover_page_data):
        """Test the relationship between Filing and CoverPageValue."""
        # Create a cover page value
        cp_value = store_cover_page_value(
            company_id=test_company.id,
            filing_id=test_filing.id,
            concept_id=test_concept.id,
            value_date=sample_cover_page_data["value_date"],
            value=sample_cover_page_data["value"],
            session=db_session
        )

        # Refresh filing object
        db_session.refresh(test_filing)

        # Verify filing has cover page values
        assert hasattr(test_filing, "cover_page_values")
        assert len(test_filing.cover_page_values) == 1
        assert test_filing.cover_page_values[0].id == cp_value.id

        # Verify value has filing
        assert cp_value.filing is not None
        assert cp_value.filing.id == test_filing.id

    def test_concept_cover_page_relationship(self, db_session, test_company, test_filing, test_concept, sample_cover_page_data):
        """Test the relationship between FinancialConcept and CoverPageValue."""
        # Create a cover page value
        cp_value = store_cover_page_value(
            company_id=test_company.id,
            filing_id=test_filing.id,
            concept_id=test_concept.id,
            value_date=sample_cover_page_data["value_date"],
            value=sample_cover_page_data["value"],
            session=db_session
        )

        # Refresh concept object
        db_session.refresh(test_concept)

        # Verify concept has cover page values
        assert hasattr(test_concept, "cover_page_values")
        assert len(test_concept.cover_page_values) == 1
        assert test_concept.cover_page_values[0].id == cp_value.id

        # Verify value has concept
        assert cp_value.concept is not None
        assert cp_value.concept.id == test_concept.id