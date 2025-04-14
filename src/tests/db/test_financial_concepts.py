"""
Tests for financial concepts operations.
"""
import pytest
from datetime import datetime

from src.python.database.crud_financial_concepts import (
    get_all_concepts,
    get_or_create_financial_concept
)
from src.python.database.models import (
    FinancialConcept
)

# Import shared fixtures (only if they're needed)
pytest.importorskip("src.tests.db.fixtures_financials")
from src.tests.db.fixtures_financials import test_company, test_filing, test_concept

class TestFinancialConcepts:
    """Test cases for financial concepts operations."""

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

    def test_get_all_concepts(self, db_session, test_company, test_filing, sample_balance_sheet_df):
        """Test retrieving all financial concepts."""
        # First, process the dataframe to create concepts
        from src.python.financial_processing import process_balance_sheet_dataframe
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