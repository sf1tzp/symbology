"""API request and response schemas."""
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentIdRequest(BaseModel):
    """Request schema for document by ID."""
    document_id: UUID = Field(..., description="UUID of the document")


class DocumentResponse(BaseModel):
    """Response schema for a document."""
    id: UUID = Field(..., description="Unique identifier for the document")
    filing_id: Optional[UUID] = Field(None, description="ID of the filing this document belongs to")
    company_id: UUID = Field(..., description="ID of the company this document belongs to")
    document_name: str = Field(..., description="Name of the document")
    content: Optional[str] = Field(None, description="Text content of the document")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174002",
                "filing_id": "123e4567-e89b-12d3-a456-426614174001",
                "company_id": "123e4567-e89b-12d3-a456-426614174000",
                "document_name": "10-K Annual Report",
                "content": "<p>This is a sample document content...</p>"
            }
        }

class DocumentContentResponse(BaseModel):
    """Response schema for document content."""
    id: UUID = Field(..., description="Unique identifier for the document")
    content: str = Field(..., description="Document content (HTML)")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174002",
                "content": "<div><p>This is the document content...</p></div>"
            }
        }