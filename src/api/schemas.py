"""API request and response schemas."""
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class PromptRole(str, Enum):
    """Enumeration of valid prompt roles."""
    SYSTEM = "system"
    ASSISTANT = "assistant"
    USER = "user"


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
    summary: Optional[str] = Field(None, description="Generated company summary based on aggregated analysis")

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
                ],
                "summary": ("Apple Inc. is a leading technology company that designs, "
                          "develops and sells consumer electronics, computer software "
                          "and online services...")
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
    # Filing information (when available)
    filing: Optional[FilingResponse] = Field(None, description="Filing information including SEC URL")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174002",
                "filing_id": "123e4567-e89b-12d3-a456-426614174001",
                "company_id": "123e4567-e89b-12d3-a456-426614174000",
                "document_name": "10-K Annual Report",
                "content": "<p>This is a sample document content...</p>",
                "filing": {
                    "id": "123e4567-e89b-12d3-a456-426614174001",
                    "company_id": "123e4567-e89b-12d3-a456-426614174000",
                    "accession_number": "0000320193-23-000077",
                    "filing_type": "10-K",
                    "filing_date": "2023-11-03",
                    "filing_url": "https://www.sec.gov/Archives/edgar/data/320193/000032019323000077/aapl-20230930.htm",
                    "period_of_report": "2023-09-30"
                }
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
    content: str = Field(..., description="Prompt content text")


class PromptResponse(BaseModel):
    """Response schema for a prompt."""
    id: UUID = Field(..., description="Unique identifier for the prompt")
    name: str = Field(..., description="Name of the prompt")
    description: Optional[str] = Field(None, description="Description of the prompt")
    role: str = Field(..., description="Role of the prompt (system, assistant, user)")
    content: str = Field(..., description="Prompt content text")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174003",
                "name": "Financial Statement Analysis",
                "description": "Analyzes financial statements from SEC filings",
                "role": "system",
                "content": "Analyze the financial statements for the company, focusing on key metrics and trends."
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
    document_ids: Optional[List[UUID]] = Field(None, description="List of document IDs used as sources")
    model: str = Field(..., description="LLM model identifier used for completion")
    temperature: Optional[float] = Field(0.7, description="Temperature parameter for the LLM")
    top_p: Optional[float] = Field(1.0, description="Top-p parameter for the LLM")
    num_ctx: Optional[int] = Field(4096, description="Context window size for the LLM")


class CompletionUpdateRequest(BaseModel):
    """Request schema for updating a completion."""
    system_prompt_id: Optional[UUID] = Field(None, description="ID of the system prompt")
    document_ids: Optional[List[UUID]] = Field(None, description="List of document IDs used as sources")
    model: Optional[str] = Field(None, description="LLM model identifier used for completion")
    temperature: Optional[float] = Field(None, description="Temperature parameter for the LLM")
    top_p: Optional[float] = Field(None, description="Top-p parameter for the LLM")
    total_duration: Optional[float] = Field(None, description="Total duration of the completion in seconds")

    class Config:
        json_schema_extra = {
            "example": {
                "system_prompt_id": "123e4567-e89b-12d3-a456-426614174003",
                "document_ids": ["123e4567-e89b-12d3-a456-426614174002"],
                "temperature": 0.5,
                "total_duration": 3.2
            }
        }


class CompletionResponse(BaseModel):
    """Response schema for a completion."""
    id: UUID = Field(..., description="Unique identifier for the completion")
    system_prompt_id: Optional[UUID] = Field(None, description="ID of the system prompt")
    model: str = Field(..., description="LLM model identifier used for completion")
    temperature: Optional[float] = Field(None, description="Temperature parameter for the LLM")
    top_p: Optional[float] = Field(None, description="Top-p parameter for the LLM")
    num_ctx: Optional[int] = Field(None, description="Context window size for the LLM")
    source_documents: List[UUID] = Field(default_factory=list, description="List of document IDs used as sources")
    created_at: datetime = Field(..., description="Timestamp when the completion was created")
    total_duration: Optional[float] = Field(None, description="Total duration of the completion in seconds")
    content: Optional[str] = Field(None, description="The actual AI-generated content of the completion")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174004",
                "system_prompt_id": "123e4567-e89b-12d3-a456-426614174003",
                "model": "gpt-4",
                "temperature": 0.7,
                "top_p": 1.0,
                "num_ctx": 4096,
                "source_documents": ["123e4567-e89b-12d3-a456-426614174002"],
                "created_at": "2023-12-25T12:30:45.123456",
                "total_duration": 2.5,
                "content": "This is the AI-generated completion content..."
            }
        }


class AggregateResponse(BaseModel):
    """Response schema for an aggregate."""
    id: UUID = Field(..., description="Unique identifier for the aggregate")
    company_id: Optional[UUID] = Field(None, description="ID of the company this aggregate belongs to")
    document_type: Optional[str] = Field(None, description="Type of document (e.g., MDA, RISK_FACTORS, DESCRIPTION)")
    created_at: datetime = Field(..., description="Timestamp when the aggregate was created")
    total_duration: Optional[float] = Field(None, description="Total duration of the aggregate generation in seconds")
    content: Optional[str] = Field(None, description="Content of the aggregate")
    summary: Optional[str] = Field(None, description="Generated summary of the aggregate content")
    model: str = Field(..., description="LLM model identifier used for the aggregate")
    temperature: Optional[float] = Field(None, description="Temperature parameter for the LLM")
    top_p: Optional[float] = Field(None, description="Top-p parameter for the LLM")
    num_ctx: Optional[int] = Field(None, description="Context window size for the LLM")
    system_prompt_id: Optional[UUID] = Field(None, description="ID of the system prompt used")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174005",
                "company_id": "123e4567-e89b-12d3-a456-426614174000",
                "document_type": "MDA",
                "created_at": "2023-12-25T12:30:45.123456",
                "total_duration": 5.2,
                "content": "This company has shown strong financial performance...",
                "summary": "Key financial highlights and strategic outlook for the company...",
                "model": "gpt-4",
                "temperature": 0.7,
                "top_p": 1.0,
                "num_ctx": 4096,
                "system_prompt_id": "123e4567-e89b-12d3-a456-426614174003"
            }
        }


# New schemas for the refactored architecture

class ModelConfigResponse(BaseModel):
    """Response schema for a model configuration."""
    id: UUID = Field(..., description="Unique identifier for the model config")
    name: str = Field(..., description="Model name")
    created_at: datetime = Field(..., description="Timestamp when the config was created")
    options: Optional[Dict[str, Any]] = Field(None, description="Ollama options as JSON")
    num_ctx: Optional[int] = Field(None, description="Context window size")
    temperature: Optional[float] = Field(None, description="Temperature parameter")
    top_k: Optional[int] = Field(None, description="Top-k parameter")
    top_p: Optional[float] = Field(None, description="Top-p parameter")
    seed: Optional[int] = Field(None, description="Random seed")
    num_predict: Optional[int] = Field(None, description="Number of tokens to predict")
    num_gpu: Optional[int] = Field(None, description="Number of GPUs to use")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174006",
                "name": "llama3.2:3b",
                "created_at": "2023-12-25T12:30:45.123456",
                "options": {"num_ctx": 4096, "temperature": 0.8},
                "num_ctx": 4096,
                "temperature": 0.8,
                "top_k": 40,
                "top_p": 0.9,
                "seed": 42,
                "num_predict": -1,
                "num_gpu": 1
            }
        }


class GeneratedContentResponse(BaseModel):
    """Response schema for generated content (consolidates Aggregate and Completion)."""
    id: UUID = Field(..., description="Unique identifier for the generated content")
    content_hash: Optional[str] = Field(None, description="SHA256 hash of the content")
    short_hash: Optional[str] = Field(None, description="Shortened hash for URLs (first 12 characters)")
    company_id: Optional[UUID] = Field(None, description="ID of the company this content belongs to")
    document_type: Optional[str] = Field(None, description="Type of document (e.g., MDA, RISK_FACTORS, DESCRIPTION)")
    source_type: str = Field(..., description="Type of sources used (documents, generated_content, both)")
    created_at: datetime = Field(..., description="Timestamp when the content was created")
    total_duration: Optional[float] = Field(None, description="Total duration of content generation in seconds")
    content: Optional[str] = Field(None, description="The actual AI-generated content")
    summary: Optional[str] = Field(None, description="Generated summary of the content")
    model_config_id: Optional[UUID] = Field(None, description="ID of the model configuration used")
    system_prompt_id: Optional[UUID] = Field(None, description="ID of the system prompt used")
    user_prompt_id: Optional[UUID] = Field(None, description="ID of the user prompt used")
    source_document_ids: List[UUID] = Field(default_factory=list, description="List of source document IDs")
    source_content_ids: List[UUID] = Field(default_factory=list, description="List of source content IDs")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174007",
                "content_hash": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2",
                "short_hash": "a1b2c3d4e5f6",
                "company_id": "123e4567-e89b-12d3-a456-426614174000",
                "document_type": "MDA",
                "source_type": "documents",
                "created_at": "2023-12-25T12:30:45.123456",
                "total_duration": 3.8,
                "content": "This comprehensive analysis of the company's financial performance...",
                "summary": "Key insights from financial analysis...",
                "model_config_id": "123e4567-e89b-12d3-a456-426614174006",
                "system_prompt_id": "123e4567-e89b-12d3-a456-426614174003",
                "user_prompt_id": None,
                "source_document_ids": ["123e4567-e89b-12d3-a456-426614174002"],
                "source_content_ids": []
            }
        }


class GeneratedContentCreateRequest(BaseModel):
    """Request schema for creating generated content."""
    company_id: Optional[UUID] = Field(None, description="ID of the company")
    document_type: Optional[str] = Field(None, description="Type of document")
    source_type: str = Field(..., description="Type of sources (documents, generated_content, both)")
    content: Optional[str] = Field(None, description="The generated content")
    summary: Optional[str] = Field(None, description="Summary of the content")
    model_config_id: Optional[UUID] = Field(None, description="ID of the model configuration")
    system_prompt_id: Optional[UUID] = Field(None, description="ID of the system prompt")
    user_prompt_id: Optional[UUID] = Field(None, description="ID of the user prompt")
    source_document_ids: Optional[List[UUID]] = Field(None, description="List of source document IDs")
    source_content_ids: Optional[List[UUID]] = Field(None, description="List of source content IDs")
    total_duration: Optional[float] = Field(None, description="Generation duration in seconds")