"""API request and response schemas."""

from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# Completion Schemas
class CompletionIdRequest(BaseModel):
    """Request schema for completion by ID."""

    completion_id: UUID = Field(..., description="UUID of the completion")


class CompletionCreateRequest(BaseModel):
    """Request schema for creating a completion."""

    system_prompt_id: Optional[UUID] = Field(
        None, description="ID of the system prompt"
    )
    user_prompt_id: Optional[UUID] = Field(None, description="ID of the user prompt")
    document_ids: Optional[List[UUID]] = Field(
        None, description="List of document IDs used as sources"
    )
    context_text: List[Dict[str, Any]] = Field(
        default_factory=list, description="Context information for the completion"
    )
    model: str = Field(..., description="LLM model identifier used for completion")
    temperature: Optional[float] = Field(
        0.7, description="Temperature parameter for the LLM"
    )
    top_p: Optional[float] = Field(1.0, description="Top-p parameter for the LLM")


class CompletionResponse(BaseModel):
    """Response schema for a completion."""

    id: UUID = Field(..., description="Unique identifier for the completion")
    system_prompt_id: Optional[UUID] = Field(
        None, description="ID of the system prompt"
    )
    user_prompt_id: Optional[UUID] = Field(None, description="ID of the user prompt")
    context_text: List[Dict[str, Any]] = Field(
        ..., description="Context information for the completion"
    )
    model: str = Field(..., description="LLM model identifier used for completion")
    temperature: Optional[float] = Field(
        None, description="Temperature parameter for the LLM"
    )
    top_p: Optional[float] = Field(None, description="Top-p parameter for the LLM")
    source_documents: List[UUID] = Field(
        default_factory=list, description="List of document IDs used as sources"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174004",
                "system_prompt_id": "123e4567-e89b-12d3-a456-426614174003",
                "user_prompt_id": "123e4567-e89b-12d3-a456-426614174005",
                "context_text": [
                    {"key": "input", "value": "Analysis of Apple's financials"}
                ],
                "model": "gpt-4",
                "temperature": 0.7,
                "top_p": 1.0,
                "source_documents": ["123e4567-e89b-12d3-a456-426614174002"],
            }
        }
