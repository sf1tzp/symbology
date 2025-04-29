"""API request and response schemas."""
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from src.llm.prompts import PromptRole


class PromptCreateRequest(BaseModel):
    """Request schema for creating a prompt."""
    name: str = Field(..., description="Name of the prompt")
    description: Optional[str] = Field(None, description="Description of the prompt")
    role: PromptRole = Field(..., description="Role of the prompt (system, assistant, user)")
    template: str = Field(..., description="Prompt template text")
    template_vars: List[str] = Field(default_factory=list, description="List of template variables")
    default_vars: Dict[str, Any] = Field(default_factory=dict, description="Default values for template variables")


class PromptResponse(BaseModel):
    """Response schema for a prompt."""
    id: UUID = Field(..., description="Unique identifier for the prompt")
    name: str = Field(..., description="Name of the prompt")
    description: Optional[str] = Field(None, description="Description of the prompt")
    role: str = Field(..., description="Role of the prompt (system, assistant, user)")
    template: str = Field(..., description="Prompt template text")
    template_vars: List[str] = Field(..., description="List of template variables")
    default_vars: Dict[str, Any] = Field(..., description="Default values for template variables")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174003",
                "name": "Financial Statement Analysis",
                "description": "Analyzes financial statements from SEC filings",
                "role": "system",
                "template": "Analyze the {statement_type} for {company_name}:\n\n{content}",
                "template_vars": ["statement_type", "company_name", "content"],
                "default_vars": {"statement_type": "income statement"}
            }
        }


class PromptsByRoleRequest(BaseModel):
    """Request schema for getting prompts by role."""
    role: PromptRole = Field(..., description="Role to filter prompts by")
