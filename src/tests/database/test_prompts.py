from typing import Any, Dict, List
import uuid

import pytest

from src.database.completions import Completion, create_completion

# Import the Prompt model and functions
from src.database.prompts import create_prompt, delete_prompt, get_prompt, get_prompt_ids, Prompt, PromptRole, update_prompt


# Sample prompt data fixtures
@pytest.fixture
def sample_system_prompt_data() -> Dict[str, Any]:
    """Sample system prompt data for testing."""
    return {
        "name": "Test System Prompt",
        "role": PromptRole.SYSTEM,  # Will be converted to PromptRole enum value
        "description": "A test system prompt for financial analysis",
        "template": "You are a helpful financial assistant that provides information about companies.",
        "template_vars": ["company_name", "industry"],
        "default_vars": {"industry": "Technology"}
    }

@pytest.fixture
def sample_user_prompt_data() -> Dict[str, Any]:
    """Sample user prompt data for testing."""
    return {
        "name": "Test User Prompt",
        "role": "user",  # Will be converted to PromptRole enum value
        "description": "A test user prompt for requesting financial analysis",
        "template": "Provide a detailed analysis of {company_name} in the {industry} industry.",
        "template_vars": ["company_name", "industry"],
        "default_vars": {"industry": "Technology"}
    }

@pytest.fixture
def sample_assistant_prompt_data() -> Dict[str, Any]:
    """Sample assistant prompt data for testing."""
    return {
        "name": "Test Assistant Prompt",
        "role": "assistant",  # Will be converted to PromptRole enum value
        "description": "A test assistant prompt for financial analysis",
        "template": "I'll analyze {company_name} in the {industry} industry for you.",
        "template_vars": ["company_name", "industry"],
        "default_vars": {"industry": "Technology"}
    }

@pytest.fixture
def multiple_prompt_data() -> List[Dict[str, Any]]:
    """Generate data for multiple prompts with different roles."""
    return [
        {
            "name": "System Prompt 1",
            "role": "system",
            "description": "System prompt for general assistance",
            "template": "You are a helpful assistant.",
            "template_vars": [],
            "default_vars": {}
        },
        {
            "name": "User Prompt 1",
            "role": "user",
            "description": "User prompt for company analysis",
            "template": "Analyze {company_name}.",
            "template_vars": ["company_name"],
            "default_vars": {}
        },
        {
            "name": "System Prompt 2",
            "role": "system",
            "description": "System prompt for financial assistance",
            "template": "You are a financial expert.",
            "template_vars": [],
            "default_vars": {}
        }
    ]

@pytest.fixture
def create_test_system_prompt(db_session, sample_system_prompt_data):
    """Create and return a test system prompt."""
    # Convert role string to enum value
    data = sample_system_prompt_data.copy()

    prompt = Prompt(**data)
    db_session.add(prompt)
    db_session.commit()
    return prompt

@pytest.fixture
def create_test_user_prompt(db_session, sample_user_prompt_data):
    """Create and return a test user prompt."""
    # Convert role string to enum value
    data = sample_user_prompt_data.copy()
    data["role"] = PromptRole.USER

    prompt = Prompt(**data)
    db_session.add(prompt)
    db_session.commit()
    return prompt

@pytest.fixture
def create_test_assistant_prompt(db_session, sample_assistant_prompt_data):
    """Create and return a test assistant prompt."""
    # Convert role string to enum value
    data = sample_assistant_prompt_data.copy()
    data["role"] = PromptRole.ASSISTANT

    prompt = Prompt(**data)
    db_session.add(prompt)
    db_session.commit()
    return prompt

@pytest.fixture
def create_test_prompts(db_session, sample_system_prompt_data, sample_user_prompt_data, sample_assistant_prompt_data):
    """Create and return test prompts of all roles."""
    prompts = []

    # Create system prompt
    system_data = sample_system_prompt_data.copy()
    system_data["role"] = PromptRole.SYSTEM
    system_prompt = Prompt(**system_data)
    db_session.add(system_prompt)
    prompts.append(system_prompt)

    # Create user prompt
    user_data = sample_user_prompt_data.copy()
    user_data["role"] = PromptRole.USER
    user_prompt = Prompt(**user_data)
    db_session.add(user_prompt)
    prompts.append(user_prompt)

    # Create assistant prompt
    assistant_data = sample_assistant_prompt_data.copy()
    assistant_data["role"] = PromptRole.ASSISTANT
    assistant_prompt = Prompt(**assistant_data)
    db_session.add(assistant_prompt)
    prompts.append(assistant_prompt)

    db_session.commit()
    return prompts

@pytest.fixture
def sample_completion_data(create_test_system_prompt, create_test_user_prompt) -> Dict[str, Any]:
    """Sample completion data for testing prompt relationships."""
    return {
        "system_prompt_id": create_test_system_prompt.id,
        "user_prompt_id": create_test_user_prompt.id,
        "model": "gpt-4",
        "temperature": 0.7,
        "top_p": 1.0,
        "context_text": [
            {"role": "system", "content": create_test_system_prompt.template},
            {"role": "user", "content": create_test_user_prompt.template}
        ]
    }

# Test cases for Prompt CRUD operations
def test_create_prompt(db_session, sample_system_prompt_data):
    """Test creating a prompt."""
    # Create prompt with proper enum conversion
    data = sample_system_prompt_data.copy()
    data["role"] = PromptRole.SYSTEM  # Use enum instead of string

    prompt = Prompt(**data)
    db_session.add(prompt)
    db_session.commit()

    # Verify it was created
    assert prompt.id is not None
    assert prompt.name == "Test System Prompt"
    assert prompt.role == PromptRole.SYSTEM
    assert len(prompt.template_vars) == 2
    assert "company_name" in prompt.template_vars
    assert "industry" in prompt.template_vars
    assert prompt.default_vars["industry"] == "Technology"

    # Verify it can be retrieved from the database
    retrieved = db_session.query(Prompt).filter_by(id=prompt.id).first()
    assert retrieved is not None
    assert retrieved.name == prompt.name
    assert retrieved.role == PromptRole.SYSTEM
    assert retrieved.template == "You are a helpful financial assistant that provides information about companies."

def test_create_prompt_with_enum(db_session):
    """Test creating a prompt with direct enum assignment."""
    prompt_data = {
        "name": "Direct Enum Prompt",
        "role": PromptRole.ASSISTANT,
        "description": "Testing direct enum assignment",
        "template": "This is a test template",
        "template_vars": [],
        "default_vars": {}
    }

    prompt = Prompt(**prompt_data)
    db_session.add(prompt)
    db_session.commit()

    # Verify it was created with the correct enum value
    retrieved = db_session.query(Prompt).filter_by(id=prompt.id).first()
    assert retrieved.role == PromptRole.ASSISTANT

def test_create_prompt_function(db_session, sample_user_prompt_data):
    """Test the create_prompt helper function."""
    # Mock the db_session global
    import src.database.prompts as prompts_module
    original_get_db_session = prompts_module.get_db_session
    prompts_module.get_db_session = lambda: db_session

    try:
        # Create a prompt using the helper function
        prompt = create_prompt(sample_user_prompt_data)

        # Verify it was created correctly
        assert prompt.id is not None
        assert prompt.name == "Test User Prompt"
        assert prompt.role == PromptRole.USER

        # Verify it exists in the database
        retrieved = db_session.query(Prompt).filter_by(id=prompt.id).first()
        assert retrieved is not None
        assert retrieved.name == prompt.name
        assert retrieved.role == PromptRole.USER
    finally:
        # Restore the original function
        prompts_module.get_db_session = original_get_db_session

def test_create_prompt_duplicate_name(db_session, create_test_system_prompt, sample_system_prompt_data):
    """Test that creating a prompt with a duplicate name raises an error."""
    # Mock the db_session global
    import src.database.prompts as prompts_module
    original_get_db_session = prompts_module.get_db_session
    prompts_module.get_db_session = lambda: db_session

    try:
        # Attempt to create a prompt with the same name
        with pytest.raises(ValueError, match="Prompt with name .* already exists"):
            create_prompt(sample_system_prompt_data)
    finally:
        # Restore the original function
        prompts_module.get_db_session = original_get_db_session

def test_create_prompt_invalid_role(db_session):
    """Test that creating a prompt with an invalid role raises an error."""
    # Mock the db_session global
    import src.database.prompts as prompts_module
    original_get_db_session = prompts_module.get_db_session
    prompts_module.get_db_session = lambda: db_session

    try:
        # Attempt to create a prompt with an invalid role
        invalid_data = {
            "name": "Invalid Role Prompt",
            "role": "invalid_role",  # This is not a valid PromptRole
            "description": "Test prompt with invalid role",
            "template": "This is a test template",
            "template_vars": [],
            "default_vars": {}
        }

        with pytest.raises(ValueError, match="Invalid role"):
            create_prompt(invalid_data)
    finally:
        # Restore the original function
        prompts_module.get_db_session = original_get_db_session

def test_get_prompt_by_id(db_session, create_test_system_prompt):
    """Test retrieving a prompt by ID using the get_prompt function."""
    # Mock the db_session global with our test session
    import src.database.prompts as prompts_module
    original_get_db_session = prompts_module.get_db_session
    prompts_module.get_db_session = lambda: db_session

    try:
        # Test the get_prompt function
        retrieved = get_prompt(create_test_system_prompt.id)
        assert retrieved is not None
        assert retrieved.id == create_test_system_prompt.id
        assert retrieved.name == create_test_system_prompt.name
        assert retrieved.role == PromptRole.SYSTEM

        # Test with non-existent ID
        non_existent = get_prompt(uuid.uuid4())
        assert non_existent is None

        # Test with string UUID
        retrieved_str = get_prompt(str(create_test_system_prompt.id))
        assert retrieved_str is not None
        assert retrieved_str.id == create_test_system_prompt.id
    finally:
        # Restore the original function
        prompts_module.get_db_session = original_get_db_session

def test_update_prompt(db_session, create_test_user_prompt):
    """Test updating a prompt using the update_prompt function."""
    # Mock the db_session global
    import src.database.prompts as prompts_module
    original_get_db_session = prompts_module.get_db_session
    prompts_module.get_db_session = lambda: db_session

    try:
        # Update the prompt
        updates = {
            "name": "Updated User Prompt",
            "description": "This prompt has been updated",
            "template": "Updated template to analyze {company_name}",
            "template_vars": ["company_name"],
            "default_vars": {"company_name": "Example Corp"}
        }

        updated = update_prompt(create_test_user_prompt.id, updates)

        # Verify updates were applied
        assert updated is not None
        assert updated.name == "Updated User Prompt"
        assert updated.description == "This prompt has been updated"
        assert updated.template == "Updated template to analyze {company_name}"
        assert updated.template_vars == ["company_name"]
        assert updated.default_vars == {"company_name": "Example Corp"}

        # Check that role wasn't changed
        assert updated.role == PromptRole.USER

        # Test updating non-existent prompt
        non_existent = update_prompt(uuid.uuid4(), {"name": "Non-existent Prompt"})
        assert non_existent is None
    finally:
        # Restore the original function
        prompts_module.get_db_session = original_get_db_session

def test_update_prompt_role(db_session, create_test_user_prompt):
    """Test updating a prompt's role."""
    # Mock the db_session global
    import src.database.prompts as prompts_module
    original_get_db_session = prompts_module.get_db_session
    prompts_module.get_db_session = lambda: db_session

    try:
        # Update the prompt's role
        updates = {
            "role": "assistant"  # Using string that will be converted to enum
        }

        updated = update_prompt(create_test_user_prompt.id, updates)

        # Verify role was updated
        assert updated is not None
        assert updated.role == PromptRole.ASSISTANT

        # Update using direct enum value
        updates = {
            "role": PromptRole.SYSTEM
        }

        updated = update_prompt(create_test_user_prompt.id, updates)
        assert updated.role == PromptRole.SYSTEM

        # Test with invalid role
        with pytest.raises(ValueError, match="Invalid role"):
            update_prompt(create_test_user_prompt.id, {"role": "invalid_role"})
    finally:
        # Restore the original function
        prompts_module.get_db_session = original_get_db_session

def test_update_prompt_name_duplicate(db_session, create_test_prompts):
    """Test that updating a prompt with a duplicate name raises an error."""
    # Mock the db_session global
    import src.database.prompts as prompts_module
    original_get_db_session = prompts_module.get_db_session
    prompts_module.get_db_session = lambda: db_session

    try:
        # Get the first two prompts
        system_prompt, user_prompt, _ = create_test_prompts

        # Try to update user prompt with system prompt's name
        with pytest.raises(ValueError, match="Prompt with name .* already exists"):
            update_prompt(user_prompt.id, {"name": system_prompt.name})
    finally:
        # Restore the original function
        prompts_module.get_db_session = original_get_db_session

def test_update_prompt_json_fields(db_session, create_test_system_prompt):
    """Test updating JSON fields in a prompt."""
    # Mock the db_session global
    import src.database.prompts as prompts_module
    original_get_db_session = prompts_module.get_db_session
    prompts_module.get_db_session = lambda: db_session

    try:
        # Update template_vars and default_vars
        updates = {
            "template_vars": ["company_name", "industry", "year"],
            "default_vars": {
                "industry": "Finance",
                "year": "2023"
            }
        }

        updated = update_prompt(create_test_system_prompt.id, updates)

        # Verify JSON fields were updated
        assert updated is not None
        assert "year" in updated.template_vars
        assert updated.default_vars["industry"] == "Finance"
        assert updated.default_vars["year"] == "2023"

        # Verify persistence by retrieving again
        retrieved = get_prompt(create_test_system_prompt.id)
        assert "year" in retrieved.template_vars
        assert retrieved.default_vars["year"] == "2023"
    finally:
        # Restore the original function
        prompts_module.get_db_session = original_get_db_session

def test_update_with_invalid_attributes(db_session, create_test_system_prompt):
    """Test updating a prompt with invalid attributes."""
    # Mock the db_session global
    import src.database.prompts as prompts_module
    original_get_db_session = prompts_module.get_db_session
    prompts_module.get_db_session = lambda: db_session

    try:
        # Update with invalid attribute
        updates = {
            "name": "Still Valid Name",
            "invalid_field": "This field doesn't exist"
        }

        # Should still update valid fields but ignore invalid ones
        updated = update_prompt(create_test_system_prompt.id, updates)
        assert updated is not None
        assert updated.name == "Still Valid Name"

        # The invalid field should not be added to the object
        assert not hasattr(updated, "invalid_field")
    finally:
        # Restore the original function
        prompts_module.get_db_session = original_get_db_session

def test_delete_prompt(db_session, create_test_assistant_prompt):
    """Test deleting a prompt using the delete_prompt function."""
    # Mock the db_session global
    import src.database.prompts as prompts_module
    original_get_db_session = prompts_module.get_db_session
    prompts_module.get_db_session = lambda: db_session

    try:
        prompt_id = create_test_assistant_prompt.id

        # Delete the prompt
        result = delete_prompt(prompt_id)
        assert result is True

        # Verify it was deleted
        assert db_session.query(Prompt).filter_by(id=prompt_id).first() is None

        # Test deleting non-existent prompt
        result = delete_prompt(uuid.uuid4())
        assert result is False

        # Test with string UUID
        new_prompt = Prompt(
            name="Test Delete String UUID",
            role=PromptRole.SYSTEM,
            template="Test template"
        )
        db_session.add(new_prompt)
        db_session.commit()

        result = delete_prompt(str(new_prompt.id))
        assert result is True
        assert db_session.query(Prompt).filter_by(id=new_prompt.id).first() is None
    finally:
        # Restore the original function
        prompts_module.get_db_session = original_get_db_session

def test_get_prompt_ids(db_session, multiple_prompt_data):
    """Test retrieving all prompt IDs."""
    # Create multiple prompts
    prompt_ids = []
    for data in multiple_prompt_data:
        data_copy = data.copy()
        data_copy["role"] = PromptRole(data_copy["role"])
        prompt = Prompt(**data_copy)
        db_session.add(prompt)
        db_session.commit()
        prompt_ids.append(prompt.id)

    # Mock the db_session global
    import src.database.prompts as prompts_module
    original_get_db_session = prompts_module.get_db_session
    prompts_module.get_db_session = lambda: db_session

    try:
        # Get all prompt IDs
        ids = get_prompt_ids()

        # Verify all created prompts are included
        for prompt_id in prompt_ids:
            assert prompt_id in ids

        # Verify count matches or exceeds (in case of existing data)
        assert len(ids) >= len(prompt_ids)
    finally:
        # Restore the original function
        prompts_module.get_db_session = original_get_db_session

def test_prompt_completion_relationship(db_session, create_test_system_prompt, create_test_user_prompt, sample_completion_data):
    """Test the relationship between prompts and completions."""
    # Create a completion associated with the prompts
    completion = Completion(**sample_completion_data)
    db_session.add(completion)
    db_session.commit()

    # Verify the relationships from completion side
    assert completion.system_prompt_id == create_test_system_prompt.id
    assert completion.user_prompt_id == create_test_user_prompt.id
    assert completion.system_prompt.name == create_test_system_prompt.name
    assert completion.user_prompt.name == create_test_user_prompt.name

    # Verify the relationships from prompt side
    system_prompt = db_session.query(Prompt).filter_by(id=create_test_system_prompt.id).first()
    user_prompt = db_session.query(Prompt).filter_by(id=create_test_user_prompt.id).first()

    assert len(system_prompt.system_completions) == 1
    assert system_prompt.system_completions[0].id == completion.id

    assert len(user_prompt.user_completions) == 1
    assert user_prompt.user_completions[0].id == completion.id

def test_create_completion_with_prompts(db_session, create_test_system_prompt, create_test_user_prompt):
    """Test creating a completion with prompt references using the create_completion function."""
    # Mock the db_session global
    import src.database.completions as completions_module
    original_get_db_session = completions_module.get_db_session
    completions_module.get_db_session = lambda: db_session

    try:
        # Create completion data with prompt references
        completion_data = {
            "system_prompt_id": create_test_system_prompt.id,
            "user_prompt_id": create_test_user_prompt.id,
            "model": "gpt-3.5-turbo",
            "context_text": [
                {"role": "system", "content": create_test_system_prompt.template},
                {"role": "user", "content": create_test_user_prompt.template}
            ]
        }

        # Create the completion
        completion = create_completion(completion_data)

        # Verify prompt relationships
        assert completion.system_prompt_id == create_test_system_prompt.id
        assert completion.user_prompt_id == create_test_user_prompt.id

        # Verify from the prompt side
        system_prompt = db_session.query(Prompt).filter_by(id=create_test_system_prompt.id).first()
        user_prompt = db_session.query(Prompt).filter_by(id=create_test_user_prompt.id).first()

        assert len(system_prompt.system_completions) == 1
        assert system_prompt.system_completions[0].id == completion.id

        assert len(user_prompt.user_completions) == 1
        assert user_prompt.user_completions[0].id == completion.id
    finally:
        # Restore the original function
        completions_module.get_db_session = original_get_db_session

def test_delete_prompt_with_completions(db_session, create_test_system_prompt, create_test_user_prompt, sample_completion_data):
    """Test that deleting a prompt doesn't delete associated completions."""
    # Create a completion with prompt associations
    completion = Completion(**sample_completion_data)
    db_session.add(completion)
    db_session.commit()
    completion_id = completion.id

    # Delete both prompts
    db_session.delete(create_test_system_prompt)
    db_session.delete(create_test_user_prompt)
    db_session.commit()

    # Verify that the completion still exists (just without the prompt references)
    completion = db_session.query(Completion).filter_by(id=completion_id).first()
    assert completion is not None
    assert completion.system_prompt_id is None
    assert completion.user_prompt_id is None