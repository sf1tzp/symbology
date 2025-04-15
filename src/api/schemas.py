"""Pydantic schemas for API request and response models."""
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, ConfigDict


class CompanyBase(BaseModel):
    """Base schema for Company data."""
    model_config = ConfigDict(from_attributes=True)

    cik: int = Field(..., description="SEC Central Index Key")
    name: str = Field(..., description="Company name")
    sic: Optional[int] = Field(None, description="Standard Industrial Classification code")
    sic_description: Optional[str] = Field(None, description="Description of SIC code")
    tickers: Optional[List[str]] = Field(None, description="Stock ticker symbols")
    exchanges: Optional[List[str]] = Field(None, description="Stock exchanges")
    ein: Optional[str] = Field(None, description="Employer Identification Number")
    state_of_incorporation: Optional[str] = Field(None, description="State where incorporated")
    fiscal_year_end: Optional[str] = Field(None, description="Month and day of fiscal year end (MM-DD)")


class CompanyCreate(CompanyBase):
    """Schema for creating a new Company."""
    pass


class CompanyUpdate(CompanyBase):
    """Schema for updating an existing Company."""
    cik: Optional[int] = None
    name: Optional[str] = None


class Company(CompanyBase):
    """Schema for Company response, including database-generated fields."""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None


class FilingBase(BaseModel):
    """Base schema for Filing data."""
    model_config = ConfigDict(from_attributes=True)

    company_id: int
    accession_number: str
    filing_type: str
    filing_date: datetime
    period_end_date: Optional[datetime] = None
    form_name: Optional[str] = None
    file_number: Optional[str] = None


class FilingCreate(FilingBase):
    """Schema for creating a new Filing."""
    pass


class FilingUpdate(FilingBase):
    """Schema for updating an existing Filing."""
    company_id: Optional[int] = None
    accession_number: Optional[str] = None
    filing_type: Optional[str] = None
    filing_date: Optional[datetime] = None


class Filing(FilingBase):
    """Schema for Filing response, including database-generated fields."""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None


class FinancialConceptBase(BaseModel):
    """Base schema for FinancialConcept data."""
    model_config = ConfigDict(from_attributes=True)

    concept_id: str
    labels: Dict[str, str]
    concept_type: Optional[str] = None
    description: Optional[str] = None


class FinancialConcept(FinancialConceptBase):
    """Schema for FinancialConcept response, including database-generated fields."""
    id: int


class FinancialValueBase(BaseModel):
    """Base schema for financial statement values."""
    model_config = ConfigDict(from_attributes=True)

    company_id: int
    filing_id: int
    concept_id: int
    value_date: datetime
    value: float


class BalanceSheetValue(FinancialValueBase):
    """Schema for balance sheet value."""
    id: int


class IncomeStatementValue(FinancialValueBase):
    """Schema for income statement value."""
    id: int


class CashFlowValue(FinancialValueBase):
    """Schema for cash flow value."""
    id: int


class FinancialStatementItem(BaseModel):
    """Schema for a financial statement item with concept information."""
    id: int
    company_id: int
    filing_id: int
    concept_id: int
    concept_name: str
    labels: Dict[str, str]
    value_date: datetime
    value: float


class FinancialStatement(BaseModel):
    """Schema for a complete financial statement."""
    company_id: int
    as_of_date: datetime
    concepts: Dict[str, Any]


class LLMCompletionBase(BaseModel):
    """Base schema for LLMCompletion data."""
    model_config = ConfigDict(from_attributes=True)

    prompt_template_id: int
    system_prompt: str
    user_prompt: str
    completion_text: str
    model: str
    temperature: float
    max_tokens: int
    company_id: Optional[int] = None
    filing_id: Optional[int] = None
    token_usage: Optional[Dict[str, int]] = None
    tags: Optional[List[str]] = None


class LLMCompletionCreate(LLMCompletionBase):
    """Schema for creating a new LLMCompletion."""
    pass


class LLMCompletion(LLMCompletionBase):
    """Schema for LLMCompletion response, including database-generated fields."""
    id: int
    created_at: datetime


class GenerationRequest(BaseModel):
    """Schema for requesting a new generation."""
    prompt: str
    system_prompt: Optional[str] = "You are a financial analyst assisting with information about companies and their financial reports."
    model: Optional[str] = "gpt-4"
    temperature: Optional[float] = 0.3
    max_tokens: Optional[int] = 1000
    company_id: Optional[int] = None
    filing_id: Optional[int] = None
    source_document_ids: Optional[List[int]] = None
    prompt_template_id: Optional[int] = None
    tags: Optional[List[str]] = None


class GenerationResponse(BaseModel):
    """Schema for generation response."""
    completion_id: int
    text: str
    model: str
    token_usage: Optional[Dict[str, int]] = None


class RatingCreate(BaseModel):
    """Schema for creating a new rating."""
    rating: int = Field(..., ge=1, le=5, description="Overall rating (1-5)")
    accuracy_score: Optional[int] = Field(None, ge=1, le=5, description="Accuracy score (1-5)")
    relevance_score: Optional[int] = Field(None, ge=1, le=5, description="Relevance score (1-5)")
    helpfulness_score: Optional[int] = Field(None, ge=1, le=5, description="Helpfulness score (1-5)")
    comments: Optional[str] = None


class RatingResponse(BaseModel):
    """Schema for rating response."""
    completion_id: int
    rating_id: int
    rating: int
    accuracy_score: Optional[int] = None
    relevance_score: Optional[int] = None
    helpfulness_score: Optional[int] = None