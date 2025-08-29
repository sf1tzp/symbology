"""Database models for model configurations."""
from datetime import datetime
import json
import hashlib
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from src.database.base import Base, get_db_session
from src.utils.logging import get_logger
from uuid_extensions import uuid7

# Initialize structlog
logger = get_logger(__name__)


class ModelConfig(Base):
    """ModelConfig model representing LLM model configurations with ollama Options."""

    __tablename__ = "model_configs"

    # Primary identifier
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)

    # Model name
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Timestamp fields
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    # All ollama Options stored as JSON - single source of truth
    options_json: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    def __repr__(self) -> str:
        return f"<ModelConfig(id={self.id}, name='{self.name}')>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert ModelConfig to dictionary for API responses."""
        return {
            "id": str(self.id),
            "name": self.name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "options": json.loads(self.options_json),
        }

    def generate_content_hash(self) -> str:
        """Generate SHA256 hash of the content for URL identification."""
        return hashlib.sha256(self.to_dict().encode('utf-8')).hexdigest()

    def get_short_hash(self, length: int = 12) -> str:
        """Get shortened version of content hash for URLs."""
        if not self.content_hash:
            return ""
        return self.content_hash[:length]

    def update_content_hash(self):
        """Update the content hash based on current content."""
        self.content_hash = self.generate_content_hash()

    @classmethod
    def from_llm_model_config(cls, model_config) -> 'ModelConfig':
        """Create a database ModelConfig from an LLM ModelConfig."""
        # Convert Options to dict, preserving all fields
        options_dict = {}
        for field_name in dir(model_config.options):
            if not field_name.startswith('_'):  # Skip private attributes
                value = getattr(model_config.options, field_name, None)
                if value is not None and not callable(value):
                    options_dict[field_name] = value

        return cls(
            name=model_config.name,
            options_json=json.dumps(options_dict, sort_keys=True)
        )

    def to_llm_model_config(self):
        """Convert database ModelConfig to LLM ModelConfig."""
        from ollama import Options
        from src.llm.client import ModelConfig as LLMModelConfig

        options_dict = json.loads(self.options_json)
        options = Options(**options_dict)

        return LLMModelConfig(name=self.name, options=options)

    # Helper properties for common access patterns
    @property
    def temperature(self) -> Optional[float]:
        """Get temperature from options."""
        options = json.loads(self.options_json)
        return options.get('temperature')

    @property
    def num_ctx(self) -> Optional[int]:
        """Get num_ctx from options."""
        options = json.loads(self.options_json)
        return options.get('num_ctx')

    @property
    def top_k(self) -> Optional[int]:
        """Get top_k from options."""
        options = json.loads(self.options_json)
        return options.get('top_k')

    @property
    def top_p(self) -> Optional[float]:
        """Get top_p from options."""
        options = json.loads(self.options_json)
        return options.get('top_p')

    @property
    def seed(self) -> Optional[int]:
        """Get seed from options."""
        options = json.loads(self.options_json)
        return options.get('seed')

    @property
    def num_predict(self) -> Optional[int]:
        """Get num_predict from options."""
        options = json.loads(self.options_json)
        return options.get('num_predict')

    @property
    def num_gpu(self) -> Optional[int]:
        """Get num_gpu from options."""
        options = json.loads(self.options_json)
        return options.get('num_gpu')


def get_model_config_ids() -> List[UUID]:
    """Get a list of all model config IDs in the database.

    Returns:
        List of model config UUIDs
    """
    try:
        session = get_db_session()
        model_config_ids = [config_id for config_id, in session.query(ModelConfig.id).all()]
        logger.info("retrieved_model_config_ids", count=len(model_config_ids))
        return model_config_ids
    except Exception as e:
        logger.error("get_model_config_ids_failed", error=str(e), exc_info=True)
        raise


def get_model_config(model_config_id: Union[UUID, str]) -> Optional[ModelConfig]:
    """Get a model config by its ID.

    Args:
        model_config_id: UUID of the model config to retrieve

    Returns:
        ModelConfig object if found, None otherwise
    """
    try:
        session = get_db_session()
        model_config = session.query(ModelConfig).filter(ModelConfig.id == model_config_id).first()
        if model_config:
            logger.info("retrieved_model_config", model_config_id=str(model_config_id))
        else:
            logger.warning("model_config_not_found", model_config_id=str(model_config_id))
        return model_config
    except Exception as e:
        logger.error("get_model_config_failed", model_config_id=str(model_config_id), error=str(e), exc_info=True)
        raise


def get_model_config_by_name(name: str) -> Optional[ModelConfig]:
    """Get a model config by its name.

    Args:
        name: Name of the model config to retrieve

    Returns:
        ModelConfig object if found, None otherwise
    """
    try:
        session = get_db_session()
        model_config = session.query(ModelConfig).filter(ModelConfig.name == name).first()
        if model_config:
            logger.info("retrieved_model_config_by_name", name=name)
        else:
            logger.warning("model_config_not_found_by_name", name=name)
        return model_config
    except Exception as e:
        logger.error("get_model_config_by_name_failed", name=name, error=str(e), exc_info=True)
        raise


def create_model_config(model_config_data: Dict[str, Any]) -> ModelConfig:
    """Create a new model config.

    Args:
        model_config_data: Dictionary containing model config data

    Returns:
        Created ModelConfig object
    """
    try:
        session = get_db_session()
        model_config = ModelConfig(**model_config_data)
        session.add(model_config)
        session.commit()
        logger.info("created_model_config", model_config_id=str(model_config.id), name=model_config.name)
        return model_config
    except Exception as e:
        session.rollback()
        logger.error("create_model_config_failed", error=str(e), exc_info=True)
        raise


def update_model_config(model_config_id: Union[UUID, str], model_config_data: Dict[str, Any]) -> Optional[ModelConfig]:
    """Update an existing model config.

    Args:
        model_config_id: UUID of the model config to update
        model_config_data: Dictionary containing updated model config data

    Returns:
        Updated ModelConfig object if found, None otherwise
    """
    try:
        session = get_db_session()
        model_config = session.query(ModelConfig).filter(ModelConfig.id == model_config_id).first()

        if model_config:
            for key, value in model_config_data.items():
                if hasattr(model_config, key):
                    setattr(model_config, key, value)

            session.commit()
            logger.info("updated_model_config", model_config_id=str(model_config_id))
            return model_config
        else:
            logger.warning("model_config_not_found_for_update", model_config_id=str(model_config_id))
            return None
    except Exception as e:
        session.rollback()
        logger.error("update_model_config_failed", model_config_id=str(model_config_id), error=str(e), exc_info=True)
        raise


def delete_model_config(model_config_id: Union[UUID, str]) -> bool:
    """Delete a model config.

    Args:
        model_config_id: UUID of the model config to delete

    Returns:
        True if model config was deleted, False if not found
    """
    try:
        session = get_db_session()
        model_config = session.query(ModelConfig).filter(ModelConfig.id == model_config_id).first()

        if model_config:
            session.delete(model_config)
            session.commit()
            logger.info("deleted_model_config", model_config_id=str(model_config_id))
            return True
        else:
            logger.warning("model_config_not_found_for_deletion", model_config_id=str(model_config_id))
            return False
    except Exception as e:
        session.rollback()
        logger.error("delete_model_config_failed", model_config_id=str(model_config_id), error=str(e), exc_info=True)
        raise


def get_all_model_configs() -> List[ModelConfig]:
    """Get all model configs.

    Returns:
        List of all ModelConfig objects
    """
    try:
        session = get_db_session()
        model_configs = session.query(ModelConfig).all()
        logger.info("retrieved_all_model_configs", count=len(model_configs))
        return model_configs
    except Exception as e:
        logger.error("get_all_model_configs_failed", error=str(e), exc_info=True)
        raise

def get_model_config_by_content_hash(content_hash: str) -> Optional[ModelConfig]:
    """Get ModelConfig by its content hash.

    Args:
        content_hash: Full or partial SHA256 hash of the prompt content

    Returns:
        ModelConfig object if found, None otherwise
    """
    try:
        session = get_db_session()

        # Try exact match first
        document = session.query(ModelConfig).filter(ModelConfig.content_hash == content_hash).first()

        # If no exact match and hash is short, try prefix match
        if not document and len(content_hash) < 64:
            document = session.query(ModelConfig).filter(
                ModelConfig.content_hash.like(f"{content_hash}%")
            ).first()

        if document:
            logger.info("retrieved_document_by_content_hash", content_hash=content_hash)
        else:
            logger.warning("document_not_found_by_content_hash", content_hash=content_hash)
        return document
    except Exception as e:
        logger.error("get_document_by_content_hash_failed", content_hash=content_hash, error=str(e), exc_info=True)
        raise