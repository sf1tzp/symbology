"""API request and response schemas."""
from datetime import date
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# Request Schemas
class CompanySearchRequest(BaseModel):
    """Request schema for company search."""
    ticker: Optional[str] = Field(None, description="Company ticker symbol")
    cik: Optional[str] = Field(None, description="Company CIK")


class CompanyIdRequest(BaseModel):
    """Request schema for company by ID."""
    company_id: UUID = Field(..., description="UUID of the company")


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

