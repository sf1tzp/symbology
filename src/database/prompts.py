import enum
import hashlib
from typing import Any, Dict, List, Optional, TYPE_CHECKING, Union
from uuid import UUID

from sqlalchemy import Enum, String, Text
from sqlalchemy.orm import attributes, Mapped, mapped_column
from src.database.base import Base, get_db_session
from src.utils.logging import get_logger
from uuid_extensions import uuid7

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
    name: Mapped[str] = mapped_column(String(255), unique=False, index=False)
    description: Mapped[Optional[str]] = mapped_column(Text)

    role: Mapped[PromptRole] = mapped_column(Enum(PromptRole), index=False)
    content: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), index=True, unique=True)


    def __repr__(self) -> str:
        return f"<Prompt(id={self.id}, desc='{self.description}', role={self.role})>"

    def pretty_print(self) -> None:
        """Pretty-print the content field of a Prompt.

        Args:
            prompt: Prompt object whose content will be printed
        """
        print(f"{self.role.value} Prompt: {self.name} (Desc: {self.description})")
        print("-" * 40)
        print(self.content)
        print("-" * 40)

    def generate_content_hash(self) -> str:
        """Generate SHA256 hash of the content for URL identification."""
        if not self.content:
            return ""

        return hashlib.sha256(self.content.encode('utf-8')).hexdigest()

    def get_short_hash(self, length: int = 12) -> str:
        """Get shortened version of content hash for URLs."""
        if not self.content_hash:
            return ""
        return self.content_hash[:length]

    def update_content_hash(self):
        """Update the content hash based on current content."""
        self.content_hash = self.generate_content_hash()

def get_prompt_ids() -> List[UUID]:
    """Get a list of all prompt IDs in the database.

    Returns:
        List of prompt UUIDs
    """
    try:
        session = get_db_session()
        prompt_ids = [prompt_id for prompt_id, in session.query(Prompt.id).all()]
        logger.debug("retrieved_prompt_ids", count=len(prompt_ids))
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


def create_prompt(prompt_data: Dict[str, Any]) -> tuple[Prompt, bool]:
    """Create a new prompt in the database.

    Args:
        prompt_data: Dictionary containing prompt attributes

    Returns:
        Tuple of (Prompt object, was_created: bool).
        was_created is True if a new prompt was created, False if existing was returned.
    """
    try:
        session = get_db_session()

        # Convert role string to enum if needed
        if 'role' in prompt_data and isinstance(prompt_data['role'], str):
            try:
                prompt_data['role'] = PromptRole(prompt_data['role'])
            except ValueError:
                valid_roles = [role.value for role in PromptRole]
                logger.error("create_prompt_failed", error=f"Invalid role '{prompt_data['role']}'. Valid roles: {valid_roles}")
                raise ValueError(f"Invalid role '{prompt_data['role']}'. Valid roles: {valid_roles}") from None

        # Create a temporary prompt to generate content hash
        temp_prompt = Prompt(**prompt_data)
        temp_prompt.update_content_hash()
        content_hash = temp_prompt.content_hash

        # Check if a prompt with the same content hash already exists
        existing_prompt = session.query(Prompt).filter(Prompt.content_hash == content_hash).first()
        if existing_prompt:
            logger.info("found_existing_prompt_with_same_content",
                       prompt_id=str(existing_prompt.id),
                       name=existing_prompt.name,
                       content_hash=content_hash)
            return existing_prompt, False

        # Create new prompt if no duplicate found
        prompt = Prompt(**prompt_data)
        prompt.update_content_hash()
        session.add(prompt)
        session.commit()
        logger.info("created_prompt", prompt_id=str(prompt.id), name=prompt.name, content_hash=content_hash)
        return prompt, True
    except Exception as e:
        session.rollback()
        logger.error("create_prompt_failed", error=str(e), exc_info=True)
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



def get_prompt_by_content_hash(content_hash: str) -> Optional[Prompt]:
    """Get prompt by its content hash.

    Args:
        content_hash: Full or partial SHA256 hash of the prompt content

    Returns:
        Prompt object if found, None otherwise
    """
    try:
        session = get_db_session()

        # Try exact match first
        document = session.query(Prompt).filter(Prompt.content_hash == content_hash).first()

        # If no exact match and hash is short, try prefix match
        if not document and len(content_hash) < 64:
            document = session.query(Prompt).filter(
                Prompt.content_hash.like(f"{content_hash}%")
            ).first()

        if document:
            logger.info("retrieved_document_by_content_hash", content_hash=content_hash)
        else:
            logger.warning("document_not_found_by_content_hash", content_hash=content_hash)
        return document
    except Exception as e:
        logger.error("get_document_by_content_hash_failed", content_hash=content_hash, error=str(e), exc_info=True)
        raise