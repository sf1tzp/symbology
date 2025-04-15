"""Pydantic schemas for API request and response models."""
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, ConfigDict


class CompanyBase(BaseModel):
    """Base schema for Company data."""
    model_config = ConfigDict(from_attributes=True)

    cik: int = Field(..., description="SEC Central Index Key")
    name: str = Field(..., description="Company name")
    sic: Optional[str] = Field(None, description="Standard Industrial Classification code")
    sic_description: Optional[str] = Field(None, description="Description of SIC code")
    tickers: Optional[List[str]] = Field(None, description="Stock ticker symbols")
    exchanges: Optional[List[str]] = Field(None, description="Stock exchanges")
    category: Optional[str] = Field(None, description="Company category")
    fiscal_year_end: Optional[str] = Field(None, description="Fiscal year end (typically in format MM-DD)")
    entity_type: Optional[str] = Field(None, description="Type of entity")
    phone: Optional[str] = Field(None, description="Contact phone number")
    flags: Optional[str] = Field(None, description="Company flags")
    business_address: Optional[str] = Field(None, description="Business address")
    mailing_address: Optional[str] = Field(None, description="Mailing address")
    insider_transaction_for_owner_exists: Optional[bool] = Field(None, description="Whether insider transactions for owner exist")
    insider_transaction_for_issuer_exists: Optional[bool] = Field(None, description="Whether insider transactions for issuer exist")
    ein: Optional[str] = Field(None, description="Employer Identification Number")
    description: Optional[str] = Field(None, description="Company description")
    website: Optional[str] = Field(None, description="Company website URL")
    investor_website: Optional[str] = Field(None, description="Investor relations website URL")
    state_of_incorporation: Optional[str] = Field(None, description="State where incorporated")
    state_of_incorporation_description: Optional[str] = Field(None, description="Description of state of incorporation")
    former_names: Optional[List[str]] = Field(None, description="Former company names")


class CompanyCreate(CompanyBase):
    """Schema for creating a new Company."""
    ticker: str


class Company(CompanyBase):

