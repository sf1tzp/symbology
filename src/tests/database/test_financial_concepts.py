from typing import Any, Dict, List
import uuid

import pytest
from sqlalchemy.exc import IntegrityError

# Import the FinancialConcept model and functions
from src.database.financial_concepts import (
    create_financial_concept,
    delete_financial_concept,
    FinancialConcept,
    get_financial_concept,
    get_financial_concept_ids,
    update_financial_concept,
)


# Sample financial concept data fixtures
@pytest.fixture
def sample_gaap_revenue_concept() -> Dict[str, Any]:
    """Sample GAAP revenue concept data for testing."""
    return {
        "name": "Revenue",
        "description": "The income generated from sale of goods or services, or any other use of capital or assets, "
                       "associated with the main operations of an organization before any costs or expenses are deducted.",
        "labels": ["Revenue", "Sales", "Net Sales", "Income", "Turnover"]
    }

@pytest.fixture
def sample_gaap_net_income_concept() -> Dict[str, Any]:
    """Sample GAAP net income concept data for testing."""
    return {
        "name": "NetIncome",
        "description": "The amount of income remaining after all expenses, including taxes, have been paid.",
        "labels": ["Net Income", "Net Earnings", "Net Profit", "Bottom Line"]
    }

@pytest.fixture
def sample_gaap_assets_concept() -> Dict[str, Any]:
    """Sample GAAP assets concept data for testing."""
    return {
        "name": "Assets",
        "description": "Resources owned or controlled by an entity that are expected to provide future economic benefits.",
        "labels": ["Total Assets", "Assets"]
    }

@pytest.fixture
def sample_gaap_liabilities_concept() -> Dict[str, Any]:
    """Sample GAAP liabilities concept data for testing."""
    return {
        "name": "Liabilities",
        "description": "Entity's obligations that are expected to reduce assets or increase other liabilities.",
        "labels": ["Total Liabilities", "Liabilities"]
    }

@pytest.fixture
def sample_gaap_minimal_concept() -> Dict[str, Any]:
    """Minimal financial concept with only required fields."""
    return {
        "name": "OperatingIncome"
    }

@pytest.fixture
def multiple_gaap_concepts() -> List[Dict[str, Any]]:
    """Generate data for multiple GAAP financial concepts."""
    return [
        {
            "name": "EarningsPerShare",
            "description": "Net income divided by the weighted average number of common shares outstanding.",
            "labels": ["EPS", "Earnings Per Share"]
        },
        {
            "name": "CostOfGoodsSold",
            "description": "The direct costs attributable to the production of the goods sold by a company.",
            "labels": ["COGS", "Cost of Sales", "Cost of Revenue"]
        },
        {
            "name": "GrossProfit",
            "description": "Revenue minus cost of goods sold.",
            "labels": ["Gross Profit", "Gross Income", "Gross Margin"]
        }
    ]

# Test cases for FinancialConcept CRUD operations
def test_create_financial_concept(db_session, sample_gaap_revenue_concept):
    """Test creating a financial concept."""
    # Create concept
    concept = FinancialConcept(**sample_gaap_revenue_concept)
    db_session.add(concept)
    db_session.commit()

    # Verify it was created
    assert concept.id is not None
    assert concept.name == "Revenue"
    assert "Sales" in concept.labels

    # Verify it can be retrieved from the database
    retrieved = db_session.query(FinancialConcept).filter_by(id=concept.id).first()
    assert retrieved is not None
    assert retrieved.name == concept.name
    assert len(retrieved.labels) == 5

def test_create_minimal_concept(db_session, sample_gaap_minimal_concept):
    """Test creating a financial concept with only required fields."""
    concept = FinancialConcept(**sample_gaap_minimal_concept)
    db_session.add(concept)
    db_session.commit()

    # Verify it was created with defaults
    assert concept.id is not None
    assert concept.name == "OperatingIncome"
    assert concept.description is None
    assert concept.labels == []

def test_get_financial_concept_by_id(db_session, sample_gaap_net_income_concept):
    """Test retrieving a financial concept by ID using the get_financial_concept function."""
    # First create a concept
    concept = FinancialConcept(**sample_gaap_net_income_concept)
    db_session.add(concept)
    db_session.commit()

    # Mock the db_session global with our test session
    import src.database.financial_concepts as concepts_module
    original_get_db_session = concepts_module.get_db_session
    concepts_module.get_db_session = lambda: db_session

    try:
        # Test the get_financial_concept function
        retrieved = get_financial_concept(concept.id)
        assert retrieved is not None
        assert retrieved.id == concept.id
        assert retrieved.name == "NetIncome"
        assert "Net Profit" in retrieved.labels

        # Test with non-existent ID
        non_existent = get_financial_concept(uuid.uuid4())
        assert non_existent is None
    finally:
        # Restore the original function
        concepts_module.get_db_session = original_get_db_session

def test_create_financial_concept_function(db_session, sample_gaap_assets_concept):
    """Test the create_financial_concept helper function."""
    # Mock the db_session global
    import src.database.financial_concepts as concepts_module
    original_get_db_session = concepts_module.get_db_session
    concepts_module.get_db_session = lambda: db_session

    try:
        # Create a concept using the helper function
        concept = create_financial_concept(sample_gaap_assets_concept)

        # Verify it was created correctly
        assert concept.id is not None
        assert concept.name == "Assets"
        assert "Total Assets" in concept.labels

        # Verify it exists in the database
        retrieved = db_session.query(FinancialConcept).filter_by(id=concept.id).first()
        assert retrieved is not None
        assert retrieved.name == concept.name
    finally:
        # Restore the original function
        concepts_module.get_db_session = original_get_db_session

def test_update_financial_concept(db_session, sample_gaap_liabilities_concept):
    """Test updating a financial concept using the update_financial_concept function."""
    # First create a concept
    concept = FinancialConcept(**sample_gaap_liabilities_concept)
    db_session.add(concept)
    db_session.commit()

    # Mock the db_session global
    import src.database.financial_concepts as concepts_module
    original_get_db_session = concepts_module.get_db_session
    concepts_module.get_db_session = lambda: db_session

    try:
        # Update the concept
        updates = {
            "description": "Updated: Legal debts or obligations that arise during the course of business operations.",
            "labels": ["Total Liabilities", "Liabilities", "Obligations"]
        }

        updated = update_financial_concept(concept.id, updates)

        # Verify updates were applied
        assert updated is not None
        assert updated.description.startswith("Updated:")
        assert len(updated.labels) == 3
        assert "Obligations" in updated.labels

        # Check that other fields weren't changed
        assert updated.name == "Liabilities"

        # Test updating non-existent concept
        non_existent = update_financial_concept(uuid.uuid4(), {"description": "Test"})
        assert non_existent is None
    finally:
        # Restore the original function
        concepts_module.get_db_session = original_get_db_session

def test_delete_financial_concept(db_session, sample_gaap_revenue_concept):
    """Test deleting a financial concept using the delete_financial_concept function."""
    # First create a concept
    concept = FinancialConcept(**sample_gaap_revenue_concept)
    db_session.add(concept)
    db_session.commit()
    concept_id = concept.id

    # Mock the db_session global
    import src.database.financial_concepts as concepts_module
    original_get_db_session = concepts_module.get_db_session
    concepts_module.get_db_session = lambda: db_session

    try:
        # Delete the concept
        result = delete_financial_concept(concept_id)
        assert result is True

        # Verify it was deleted
        assert db_session.query(FinancialConcept).filter_by(id=concept_id).first() is None

        # Test deleting non-existent concept
        result = delete_financial_concept(uuid.uuid4())
        assert result is False
    finally:
        # Restore the original function
        concepts_module.get_db_session = original_get_db_session

def test_get_financial_concept_ids(db_session, multiple_gaap_concepts):
    """Test retrieving all financial concept IDs."""
    # Create multiple concepts
    concept_ids = []
    for data in multiple_gaap_concepts:
        concept = FinancialConcept(**data)
        db_session.add(concept)
        db_session.commit()
        concept_ids.append(concept.id)

    # Mock the db_session global
    import src.database.financial_concepts as concepts_module
    original_get_db_session = concepts_module.get_db_session
    concepts_module.get_db_session = lambda: db_session

    try:
        # Get all concept IDs
        ids = get_financial_concept_ids()

        # Verify all created concepts are included
        for concept_id in concept_ids:
            assert concept_id in ids

        # Verify count matches
        assert len(ids) >= len(concept_ids)
    finally:
        # Restore the original function
        concepts_module.get_db_session = original_get_db_session

def test_duplicate_concept_name(db_session, sample_gaap_revenue_concept):
    """Test that creating concepts with duplicate names fails."""
    # Create first concept
    concept1 = FinancialConcept(**sample_gaap_revenue_concept)
    db_session.add(concept1)
    db_session.commit()

    # Try to create second concept with same name
    concept2_data = sample_gaap_revenue_concept.copy()
    concept2_data["description"] = "Duplicate name test"
    concept2 = FinancialConcept(**concept2_data)
    db_session.add(concept2)

    # Should raise IntegrityError due to unique constraint
    with pytest.raises(IntegrityError):
        db_session.commit()

def test_update_with_invalid_attributes(db_session, sample_gaap_assets_concept):
    """Test updating a financial concept with invalid attributes."""
    # First create a concept
    concept = FinancialConcept(**sample_gaap_assets_concept)
    db_session.add(concept)
    db_session.commit()

    # Mock the db_session global
    import src.database.financial_concepts as concepts_module
    original_get_db_session = concepts_module.get_db_session
    concepts_module.get_db_session = lambda: db_session

    try:
        # Update with invalid attribute
        updates = {
            "description": "Valid update description",
            "invalid_field": "This field doesn't exist"
        }

        # Should still update valid fields but ignore invalid ones
        updated = update_financial_concept(concept.id, updates)
        assert updated is not None
        assert updated.description == "Valid update description"

        # The invalid field should not be added to the object
        assert not hasattr(updated, "invalid_field")
    finally:
        # Restore the original function
        concepts_module.get_db_session = original_get_db_session

def test_create_duplicate_name_via_function(db_session, sample_gaap_net_income_concept):
    """Test that the create_financial_concept function handles duplicate names correctly."""
    # Mock the db_session global
    import src.database.financial_concepts as concepts_module
    original_get_db_session = concepts_module.get_db_session
    concepts_module.get_db_session = lambda: db_session

    try:
        # Create first concept
        concept1 = create_financial_concept(sample_gaap_net_income_concept)
        assert concept1 is not None

        # Try to create second concept with same name - should raise ValueError
        with pytest.raises(ValueError):
            create_financial_concept(sample_gaap_net_income_concept)
    finally:
        # Restore the original function
        concepts_module.get_db_session = original_get_db_session

def test_update_with_existing_name(db_session, sample_gaap_revenue_concept, sample_gaap_net_income_concept):
    """Test that updating a concept to use an existing name is prevented."""
    # Create two concepts
    concept1 = FinancialConcept(**sample_gaap_revenue_concept)
    concept2 = FinancialConcept(**sample_gaap_net_income_concept)
    db_session.add(concept1)
    db_session.add(concept2)
    db_session.commit()

    # Mock the db_session global
    import src.database.financial_concepts as concepts_module
    original_get_db_session = concepts_module.get_db_session
    concepts_module.get_db_session = lambda: db_session

    try:
        # Try to update concept2 to use concept1's name
        updates = {"name": "Revenue"}

        # Should raise ValueError
        with pytest.raises(ValueError):
            update_financial_concept(concept2.id, updates)
    finally:
        # Restore the original function
        concepts_module.get_db_session = original_get_db_session

def test_get_financial_concept_with_string_uuid(db_session, sample_gaap_assets_concept):
    """Test retrieving a financial concept using string representation of UUID."""
    # First create a concept
    concept = FinancialConcept(**sample_gaap_assets_concept)
    db_session.add(concept)
    db_session.commit()

    # Mock the db_session global
    import src.database.financial_concepts as concepts_module
    original_get_db_session = concepts_module.get_db_session
    concepts_module.get_db_session = lambda: db_session

    try:
        # Test get_financial_concept with string UUID
        retrieved = get_financial_concept(str(concept.id))
        assert retrieved is not None
        assert retrieved.id == concept.id
        assert retrieved.name == "Assets"
    finally:
        # Restore the original function
        concepts_module.get_db_session = original_get_db_session

def test_find_or_create_financial_concept(db_session):
    """Test the find_or_create_financial_concept helper function."""
    # Mock the db_session global
    import src.database.financial_concepts as concepts_module
    original_get_db_session = concepts_module.get_db_session
    concepts_module.get_db_session = lambda: db_session

    try:
        # Create a new concept using find_or_create
        concept = concepts_module.find_or_create_financial_concept(
            name="Revenue",
            description="The income generated from sale of goods or services.",
            labels=["income_statement"]
        )

        assert concept is not None
        assert concept.name == "Revenue"
        assert concept.description == "The income generated from sale of goods or services."
        assert "income_statement" in concept.labels
        concept_id = concept.id

        # Call find_or_create again with the same name - should return existing concept
        concept2 = concepts_module.find_or_create_financial_concept(
            name="Revenue",
            description="Total revenues of the company.",
            labels=["income_statement", "top_line"]
        )

        # Should be same concept but with updated info
        assert concept2.id == concept_id
        assert concept2.description == "Total revenues of the company."
        assert "income_statement" in concept2.labels
        assert "top_line" in concept2.labels
        assert len(concept2.labels) == 2

        # Test with just a name
        minimal_concept = concepts_module.find_or_create_financial_concept(
            name="OperatingIncome"
        )

        assert minimal_concept is not None
        assert minimal_concept.name == "OperatingIncome"
        assert minimal_concept.description is None
        assert minimal_concept.labels == []
    finally:
        # Restore the original function
        concepts_module.get_db_session = original_get_db_session

def test_find_or_create_financial_concept_merges_labels(db_session):
    """Test that find_or_create_financial_concept merges labels properly."""
    # First create a concept directly
    concept_data = {
        "name": "GrossProfit",
        "description": "Revenue minus cost of goods sold.",
        "labels": ["income_statement", "profit"]
    }
    concept = FinancialConcept(**concept_data)
    db_session.add(concept)
    db_session.commit()
    concept_id = concept.id

    # Mock the db_session global
    import src.database.financial_concepts as concepts_module
    original_get_db_session = concepts_module.get_db_session
    concepts_module.get_db_session = lambda: db_session

    try:
        # Now try to find_or_create with same name but different labels
        updated_concept = concepts_module.find_or_create_financial_concept(
            name="GrossProfit",
            description="Revenue minus COGS.",
            labels=["profit", "core_metric", "margin"]
        )

        # Should be the same concept with merged labels
        assert updated_concept.id == concept_id
        assert updated_concept.description == "Revenue minus COGS."

        # Should have merged labels without duplicates
        assert len(updated_concept.labels) == 4
        assert "income_statement" in updated_concept.labels
        assert "profit" in updated_concept.labels
        assert "core_metric" in updated_concept.labels
        assert "margin" in updated_concept.labels
    finally:
        # Restore the original function
        concepts_module.get_db_session = original_get_db_session

def test_get_financial_concept_by_name(db_session, sample_gaap_net_income_concept):
    """Test the get_financial_concept_by_name helper function."""
    # First create a concept
    concept = FinancialConcept(**sample_gaap_net_income_concept)
    db_session.add(concept)
    db_session.commit()

    # Mock the db_session global
    import src.database.financial_concepts as concepts_module
    original_get_db_session = concepts_module.get_db_session
    concepts_module.get_db_session = lambda: db_session

    try:
        # Test retrieving by name
        retrieved = concepts_module.get_financial_concept_by_name("NetIncome")
        assert retrieved is not None
        assert retrieved.id == concept.id
        assert retrieved.description == sample_gaap_net_income_concept["description"]

        # Test with non-existent name
        non_existent = concepts_module.get_financial_concept_by_name("NonExistentConcept")
        assert non_existent is None
    finally:
        # Restore the original function
        concepts_module.get_db_session = original_get_db_session