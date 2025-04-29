"""API request and response schemas."""
from datetime import date
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class FilingIdRequest(BaseModel):
    """Request schema for filing by ID."""
    filing_id: UUID = Field(..., description="UUID of the filing")


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

