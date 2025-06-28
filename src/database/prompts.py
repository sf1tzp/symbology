import enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING, Union
from uuid import UUID

from sqlalchemy import Enum, String, Text
from sqlalchemy.orm import attributes, Mapped, mapped_column
from uuid_extensions import uuid7

from src.database.base import Base, get_db_session
from src.utils.logging import get_logger

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    pass

# Initialize structlog
logger = get_logger(__name__)

class PromptRole(enum.Enum):
    """Enumeration of valid prompt roles."""
    SYSTEM = "system"
    ASSISTANT = "assistant"
    USER = "user"

class Prompt(Base):
    """Prompt model representing prompt templates."""

    __tablename__ = "prompts"

    # Primary identifier
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)

    # Prompt details
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)

    role: Mapped[PromptRole] = mapped_column(Enum(PromptRole), index=True)
    content: Mapped[str] = mapped_column(Text)


    def __repr__(self) -> str:
        return f"<Prompt(id={self.id}, name='{self.name}', role={self.role})>"


def get_prompt_ids() -> List[UUID]:
    """Get a list of all prompt IDs in the database.

    Returns:
        List of prompt UUIDs
    """
    try:
        session = get_db_session()
        prompt_ids = [prompt_id for prompt_id, in session.query(Prompt.id).all()]
        logger.info("retrieved_prompt_ids", count=len(prompt_ids))
        return prompt_ids
    except Exception as e:
        logger.error("get_prompt_ids_failed", error=str(e), exc_info=True)
        raise


def get_prompt(prompt_id: Union[UUID, str]) -> Optional[Prompt]:
    """Get a prompt by its ID.

    Args:
        prompt_id: UUID of the prompt to retrieve

    Returns:
        Prompt object if found, None otherwise
    """
    try:
        session = get_db_session()
        prompt = session.query(Prompt).filter(Prompt.id == prompt_id).first()
        if prompt:
            logger.info("retrieved_prompt", prompt_id=str(prompt_id))
        else:
            logger.warning("prompt_not_found", prompt_id=str(prompt_id))
        return prompt
    except Exception as e:
        logger.error("get_prompt_failed", prompt_id=str(prompt_id), error=str(e), exc_info=True)
        raise


def create_prompt(prompt_data: Dict[str, Any]) -> Prompt:
    """Create a new prompt in the database.

    Args:
        prompt_data: Dictionary containing prompt attributes

    Returns:
        Newly created Prompt object
    """
    try:
        session = get_db_session()

        # Check if a prompt with the same name already exists
        name = prompt_data.get('name')
        if name and session.query(Prompt).filter(Prompt.name == name).first():
            logger.error("create_prompt_failed", error=f"Prompt with name '{name}' already exists")
            raise ValueError(f"Prompt with name '{name}' already exists")

        # Convert role string to enum if needed
        if 'role' in prompt_data and isinstance(prompt_data['role'], str):
            try:
                prompt_data['role'] = PromptRole(prompt_data['role'])
            except ValueError:
                valid_roles = [role.value for role in PromptRole]
                logger.error("create_prompt_failed", error=f"Invalid role '{prompt_data['role']}'. Valid roles: {valid_roles}")
                raise ValueError(f"Invalid role '{prompt_data['role']}'. Valid roles: {valid_roles}") from None

        prompt = Prompt(**prompt_data)
        session.add(prompt)
        session.commit()
        logger.info("created_prompt", prompt_id=str(prompt.id), name=prompt.name)
        return prompt
    except Exception as e:
        session.rollback()
        logger.error("create_prompt_failed", error=str(e), exc_info=True)
        raise


def update_prompt(prompt_id: Union[UUID, str], prompt_data: Dict[str, Any]) -> Optional[Prompt]:
    """Update an existing prompt in the database.

    Args:
        prompt_id: UUID of the prompt to update
        prompt_data: Dictionary containing prompt attributes to update

    Returns:
        Updated Prompt object if found, None otherwise
    """
    try:
        session = get_db_session()
        prompt = session.query(Prompt).filter(Prompt.id == prompt_id).first()
        if not prompt:
            logger.warning("update_prompt_not_found", prompt_id=str(prompt_id))
            return None

        # If name is being updated, check if it already exists for another prompt
        if 'name' in prompt_data and prompt_data['name'] != prompt.name:
            existing = session.query(Prompt).filter(
                Prompt.name == prompt_data['name'],
                Prompt.id != prompt_id
            ).first()
            if existing:
                logger.error(
                    "update_prompt_failed",
                    error=f"Prompt with name '{prompt_data['name']}' already exists"
                )
                raise ValueError(f"Prompt with name '{prompt_data['name']}' already exists")

        # Convert role string to enum if needed
        if 'role' in prompt_data and isinstance(prompt_data['role'], str):
            try:
                prompt_data['role'] = PromptRole(prompt_data['role'])
            except ValueError:
                valid_roles = [role.value for role in PromptRole]
                logger.error("update_prompt_failed", error=f"Invalid role '{prompt_data['role']}'. Valid roles: {valid_roles}")
                raise ValueError(f"Invalid role '{prompt_data['role']}'. Valid roles: {valid_roles}") from None

        for key, value in prompt_data.items():
            if hasattr(prompt, key):
                setattr(prompt, key, value)
                # Flag JSON fields as modified to ensure changes are detected
                if key in ['template_vars', 'default_vars']:
                    attributes.flag_modified(prompt, key)
            else:
                logger.warning("update_prompt_invalid_attribute", prompt_id=str(prompt_id), attribute=key)

        session.commit()
        logger.info("updated_prompt", prompt_id=str(prompt.id), name=prompt.name)
        return prompt
    except Exception as e:
        session.rollback()
        logger.error("update_prompt_failed", prompt_id=str(prompt_id), error=str(e), exc_info=True)
        raise


def delete_prompt(prompt_id: Union[UUID, str]) -> bool:
    """Delete a prompt from the database.

    Args:
        prompt_id: UUID of the prompt to delete

    Returns:
        True if prompt was deleted, False if not found
    """
    try:
        session = get_db_session()
        prompt = session.query(Prompt).filter(Prompt.id == prompt_id).first()
        if not prompt:
            logger.warning("delete_prompt_not_found", prompt_id=str(prompt_id))
            return False

        session.delete(prompt)
        session.commit()
        logger.info("deleted_prompt", prompt_id=str(prompt_id))
        return True
    except Exception as e:
        session.rollback()
        logger.error("delete_prompt_failed", prompt_id=str(prompt_id), error=str(e), exc_info=True)
        raise


def get_prompt_by_name(name: str) -> Optional[Prompt]:
    """Get a prompt by its name.

    Args:
        name: Name of the prompt to retrieve

    Returns:
        Prompt object if found, None otherwise
    """
    try:
        session = get_db_session()
        prompt = session.query(Prompt).filter(Prompt.name == name).first()
        if prompt:
            logger.info("retrieved_prompt_by_name", name=name, prompt_id=str(prompt.id))
        else:
            logger.warning("prompt_by_name_not_found", name=name)
        return prompt
    except Exception as e:
        logger.error("get_prompt_by_name_failed", name=name, error=str(e), exc_info=True)
        raise