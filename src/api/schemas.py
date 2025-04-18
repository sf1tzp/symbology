"""API request and response schemas."""
from datetime import date
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from src.llm.prompts import PromptRole


# Request Schemas
class CompanySearchRequest(BaseModel):
    """Request schema for company search."""
    ticker: Optional[str] = Field(None, description="Company ticker symbol")
    cik: Optional[str] = Field(None, description="Company CIK")


class CompanyIdRequest(BaseModel):
    """Request schema for company by ID."""
    company_id: UUID = Field(..., description="UUID of the company")


class FilingIdRequest(BaseModel):
    """Request schema for filing by ID."""
    filing_id: UUID = Field(..., description="UUID of the filing")


class DocumentIdRequest(BaseModel):
    """Request schema for document by ID."""
    document_id: UUID = Field(..., description="UUID of the document")


# Response Schemas
class CompanyResponse(BaseModel):
    """Response schema for a company."""
    id: UUID = Field(..., description="Unique identifier for the company")
    cik: Optional[str] = Field(None, description="Company CIK (Central Index Key)")
    name: str = Field(..., description="Company name")
    display_name: Optional[str] = Field(None, description="Display name for the company")
    is_company: bool = Field(True, description="Whether this is a company or not")
    tickers: List[str] = Field(default_factory=list, description="List of ticker symbols")
    exchanges: List[str] = Field(default_factory=list, description="List of exchanges where company is listed")
    sic: Optional[str] = Field(None, description="Standard Industrial Classification code")
    sic_description: Optional[str] = Field(None, description="Description of the SIC code")
    fiscal_year_end: Optional[date] = Field(None, description="Date of fiscal year end")
    entity_type: Optional[str] = Field(None, description="Type of entity")
    ein: Optional[str] = Field(None, description="Employer Identification Number")
    former_names: List[Dict[str, Any]] = Field(default_factory=list, description="List of former company names")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "cik": "0000320193",
                "name": "Apple Inc.",
                "display_name": "Apple Inc.",
                "is_company": True,
                "tickers": ["AAPL"],
                "exchanges": ["NASDAQ"],
                "sic": "3571",
                "sic_description": "Electronic Computers",
                "fiscal_year_end": "2023-09-30",
                "entity_type": "CORPORATION",
                "ein": "94-2404110",
                "former_names": [
                    {
                        "name": "Apple Computer, Inc.",
                        "date_changed": "2007-01-09"
                    }
                ]
            }
        }


class FilingResponse(BaseModel):
    """Response schema for a filing."""
    id: UUID = Field(..., description="Unique identifier for the filing")
    company_id: UUID = Field(..., description="ID of the company this filing belongs to")
    accession_number: str = Field(..., description="SEC accession number")
    filing_type: str = Field(..., description="SEC filing type (e.g., 10-K, 10-Q)")
    filing_date: date = Field(..., description="Date the filing was submitted")
    filing_url: Optional[str] = Field(None, description="URL to the filing on SEC website")
    period_of_report: Optional[date] = Field(None, description="Period covered by the report")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174001",
                "company_id": "123e4567-e89b-12d3-a456-426614174000",
                "accession_number": "0000320193-23-000077",
                "filing_type": "10-K",
                "filing_date": "2023-11-03",
                "filing_url": "https://www.sec.gov/Archives/edgar/data/320193/000032019323000077/aapl-20230930.htm",
                "period_of_report": "2023-09-30"
            }
        }


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


# Completion Schemas
class CompletionIdRequest(BaseModel):
    """Request schema for completion by ID."""
    completion_id: UUID = Field(..., description="UUID of the completion")


class CompletionCreateRequest(BaseModel):
    """Request schema for creating a completion."""
    system_prompt_id: Optional[UUID] = Field(None, description="ID of the system prompt")
    user_prompt_id: Optional[UUID] = Field(None, description="ID of the user prompt")
    document_ids: Optional[List[UUID]] = Field(None, description="List of document IDs used as sources")
    context_text: List[Dict[str, Any]] = Field(default_factory=list, description="Context information for the completion")
    model: str = Field(..., description="LLM model identifier used for completion")
    temperature: Optional[float] = Field(0.7, description="Temperature parameter for the LLM")
    top_p: Optional[float] = Field(1.0, description="Top-p parameter for the LLM")


class CompletionResponse(BaseModel):
    """Response schema for a completion."""
    id: UUID = Field(..., description="Unique identifier for the completion")
    system_prompt_id: Optional[UUID] = Field(None, description="ID of the system prompt")
    user_prompt_id: Optional[UUID] = Field(None, description="ID of the user prompt")
    context_text: List[Dict[str, Any]] = Field(..., description="Context information for the completion")
    model: str = Field(..., description="LLM model identifier used for completion")
    temperature: Optional[float] = Field(None, description="Temperature parameter for the LLM")
    top_p: Optional[float] = Field(None, description="Top-p parameter for the LLM")
    source_documents: List[UUID] = Field(default_factory=list, description="List of document IDs used as sources")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174004",
                "system_prompt_id": "123e4567-e89b-12d3-a456-426614174003",
                "user_prompt_id": "123e4567-e89b-12d3-a456-426614174005",
                "context_text": [{"key": "input", "value": "Analysis of Apple's financials"}],
                "model": "gpt-4",
                "temperature": 0.7,
                "top_p": 1.0,
                "source_documents": ["123e4567-e89b-12d3-a456-426614174002"]
            }
        }