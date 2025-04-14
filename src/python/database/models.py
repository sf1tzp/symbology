from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from .base import Base


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True)
    cik = Column(Integer, index=True, unique=True)
    name = Column(String(255), nullable=False)
    tickers = Column(JSON)  # List of ticker symbols
    exchanges = Column(JSON)  # List of exchanges
    sic = Column(String(10))
    sic_description = Column(String(255))
    category = Column(String(100))
    fiscal_year_end = Column(String(4))
    entity_type = Column(String(50))
    phone = Column(String(20))
    flags = Column(String(100))
    business_address = Column(Text)
    mailing_address = Column(Text)
    insider_transaction_for_owner_exists = Column(Boolean, default=False)
    insider_transaction_for_issuer_exists = Column(Boolean, default=False)
    ein = Column(String(20))
    description = Column(Text)
    website = Column(String(255))
    investor_website = Column(String(255))
    state_of_incorporation = Column(String(2))
    state_of_incorporation_description = Column(String(50))
    former_names = Column(JSON)  # List of former company names

    # Relationship with filings
    filings = relationship("Filing", back_populates="company")
    # Relationship with balance sheet values
    balance_sheet_values = relationship("BalanceSheetValue", back_populates="company")
    # Relationship with income statement values
    income_statement_values = relationship("IncomeStatementValue", back_populates="company")
    # Relationship with cash flow statement values
    cash_flow_statement_values = relationship("CashFlowStatementValue", back_populates="company")
    # Relationship with cover page values
    cover_page_values = relationship("CoverPageValue", back_populates="company")

    def __repr__(self):
        return f"<Company(name='{self.name}', cik={self.cik}, tickers={self.tickers})>"

    def to_dict(self):
        """Convert Company object to dictionary"""
        result = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        return result

    def to_json(self):
        """Convert Company object to JSON string"""
        import json
        return json.dumps(self.to_dict(), default=str)


class Filing(Base):
    __tablename__ = "filings"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True, nullable=False)
    filing_type = Column(String(20), index=True, nullable=False)  # e.g., 10-K, 10-Q, 8-K
    accession_number = Column(String(20), index=True, unique=True)
    filing_date = Column(DateTime, index=True)
    report_date = Column(DateTime, index=True)
    form_name = Column(String(100))
    file_number = Column(String(20))
    film_number = Column(String(20))
    description = Column(Text)
    url = Column(String(255))
    data = Column(JSON)  # For storing parsed filing data

    # Relationship with company
    company = relationship("Company", back_populates="filings")
    # Relationship with balance sheet values
    balance_sheet_values = relationship("BalanceSheetValue", back_populates="filing")
    # Relationship with income statement values
    income_statement_values = relationship("IncomeStatementValue", back_populates="filing")
    # Relationship with cash flow statement values
    cash_flow_statement_values = relationship("CashFlowStatementValue", back_populates="filing")
    # Relationship with cover page values
    cover_page_values = relationship("CoverPageValue", back_populates="filing")
    # Relationship with document sections
    business_description = relationship("BusinessDescription", back_populates="filing", uselist=False)
    risk_factors = relationship("RiskFactors", back_populates="filing", uselist=False)
    management_discussion = relationship("ManagementDiscussion", back_populates="filing", uselist=False)

    def __repr__(self):
        return f"<Filing(id={self.id}, type='{self.filing_type}', date={self.filing_date})>"

    def to_dict(self):
        """Convert Filing object to dictionary"""
        result = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        return result

    def to_json(self):
        """Convert Filing object to JSON string"""
        import json
        return json.dumps(self.to_dict(), default=str)


class FinancialConcept(Base):
    """Model for tracking financial concepts and their labels across companies."""
    __tablename__ = "financial_concepts"

    id = Column(Integer, primary_key=True)
    concept_id = Column(String(255), index=True, unique=True, nullable=False)  # e.g., "us-gaap_CashAndCashEquivalentsAtCarryingValue"
    description = Column(Text)
    labels = Column(JSON)  # Array of different labels used for this concept

    # Relationship with balance sheet values
    balance_sheet_values = relationship("BalanceSheetValue", back_populates="concept")
    # Relationship with income statement values
    income_statement_values = relationship("IncomeStatementValue", back_populates="concept")
    # Relationship with cash flow statement values
    cash_flow_statement_values = relationship("CashFlowStatementValue", back_populates="concept")
    # Relationship with cover page values
    cover_page_values = relationship("CoverPageValue", back_populates="concept")

    def __repr__(self):
        return f"<FinancialConcept(concept_id='{self.concept_id}')>"

    def to_dict(self):
        """Convert FinancialConcept object to dictionary"""
        result = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        return result

    def to_json(self):
        """Convert FinancialConcept object to JSON string"""
        import json
        return json.dumps(self.to_dict(), default=str)


class BalanceSheetValue(Base):
    """Model for storing balance sheet values for companies."""
    __tablename__ = "balance_sheet_values"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True, nullable=False)
    filing_id = Column(Integer, ForeignKey("filings.id"), index=True, nullable=False)
    concept_id = Column(Integer, ForeignKey("financial_concepts.id"), index=True, nullable=False)
    value_date = Column(DateTime, index=True, nullable=False)
    value = Column(Float)

    # Relationships
    company = relationship("Company", back_populates="balance_sheet_values")
    filing = relationship("Filing", back_populates="balance_sheet_values")
    concept = relationship("FinancialConcept", back_populates="balance_sheet_values")

    def __repr__(self):
        return f"<BalanceSheetValue(company_id={self.company_id}, concept_id={self.concept_id}, value_date={self.value_date})>"

    def to_dict(self):
        """Convert BalanceSheetValue object to dictionary"""
        result = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        return result

    def to_json(self):
        """Convert BalanceSheetValue object to JSON string"""
        import json
        return json.dumps(self.to_dict(), default=str)


class IncomeStatementValue(Base):
    """Model for storing income statement values for companies."""
    __tablename__ = "income_statement_values"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True, nullable=False)
    filing_id = Column(Integer, ForeignKey("filings.id"), index=True, nullable=False)
    concept_id = Column(Integer, ForeignKey("financial_concepts.id"), index=True, nullable=False)
    value_date = Column(DateTime, index=True, nullable=False)
    value = Column(Float)

    # Relationships
    company = relationship("Company", back_populates="income_statement_values")
    filing = relationship("Filing", back_populates="income_statement_values")
    concept = relationship("FinancialConcept", back_populates="income_statement_values")

    def __repr__(self):
        return f"<IncomeStatementValue(company_id={self.company_id}, concept_id={self.concept_id}, value_date={self.value_date})>"

    def to_dict(self):
        """Convert IncomeStatementValue object to dictionary"""
        result = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        return result

    def to_json(self):
        """Convert IncomeStatementValue object to JSON string"""
        import json
        return json.dumps(self.to_dict(), default=str)


class CashFlowStatementValue(Base):
    """Model for storing cash flow statement values for companies."""
    __tablename__ = "cash_flow_statement_values"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True, nullable=False)
    filing_id = Column(Integer, ForeignKey("filings.id"), index=True, nullable=False)
    concept_id = Column(Integer, ForeignKey("financial_concepts.id"), index=True, nullable=False)
    value_date = Column(DateTime, index=True, nullable=False)
    value = Column(Float)

    # Relationships
    company = relationship("Company", back_populates="cash_flow_statement_values")
    filing = relationship("Filing", back_populates="cash_flow_statement_values")
    concept = relationship("FinancialConcept", back_populates="cash_flow_statement_values")

    def __repr__(self):
        return f"<CashFlowStatementValue(company_id={self.company_id}, concept_id={self.concept_id}, value_date={self.value_date})>"

    def to_dict(self):
        """Convert CashFlowStatementValue object to dictionary"""
        result = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        return result

    def to_json(self):
        """Convert CashFlowStatementValue object to JSON string"""
        import json
        return json.dumps(self.to_dict(), default=str)


class CoverPageValue(Base):
    """Model for storing cover page values for companies."""
    __tablename__ = "cover_page_values"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True, nullable=False)
    filing_id = Column(Integer, ForeignKey("filings.id"), index=True, nullable=False)
    concept_id = Column(Integer, ForeignKey("financial_concepts.id"), index=True, nullable=False)
    value_date = Column(DateTime, index=True, nullable=False)
    value = Column(Float)

    # Relationships
    company = relationship("Company", back_populates="cover_page_values")
    filing = relationship("Filing", back_populates="cover_page_values")
    concept = relationship("FinancialConcept", back_populates="cover_page_values")

    def __repr__(self):
        return f"<CoverPageValue(company_id={self.company_id}, concept_id={self.concept_id}, value_date={self.value_date})>"

    def to_dict(self):
        """Convert CoverPageValue object to dictionary"""
        result = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        return result

    def to_json(self):
        """Convert CoverPageValue object to JSON string"""
        import json
        return json.dumps(self.to_dict(), default=str)


class BusinessDescription(Base):
    """Model for storing business description sections from 10-K filings."""
    __tablename__ = "business_descriptions"

    id = Column(Integer, primary_key=True)
    filing_id = Column(Integer, ForeignKey("filings.id"), index=True, unique=True, nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True, nullable=False)
    report_date = Column(DateTime, index=True, nullable=False)
    content = Column(Text, nullable=False)

    # Relationships
    filing = relationship("Filing", back_populates="business_description")
    company = relationship("Company")

    def __repr__(self):
        return f"<BusinessDescription(filing_id={self.filing_id}, company_id={self.company_id})>"

    def to_dict(self):
        """Convert BusinessDescription object to dictionary"""
        result = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        return result

    def to_json(self):
        """Convert BusinessDescription object to JSON string"""
        import json
        return json.dumps(self.to_dict(), default=str)


class RiskFactors(Base):
    """Model for storing risk factors sections from 10-K filings."""
    __tablename__ = "risk_factors"

    id = Column(Integer, primary_key=True)
    filing_id = Column(Integer, ForeignKey("filings.id"), index=True, unique=True, nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True, nullable=False)
    report_date = Column(DateTime, index=True, nullable=False)
    content = Column(Text, nullable=False)

    # Relationships
    filing = relationship("Filing", back_populates="risk_factors")
    company = relationship("Company")

    def __repr__(self):
        return f"<RiskFactors(filing_id={self.filing_id}, company_id={self.company_id})>"

    def to_dict(self):
        """Convert RiskFactors object to dictionary"""
        result = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        return result

    def to_json(self):
        """Convert RiskFactors object to JSON string"""
        import json
        return json.dumps(self.to_dict(), default=str)


class ManagementDiscussion(Base):
    """Model for storing management discussion sections from 10-K filings."""
    __tablename__ = "management_discussions"

    id = Column(Integer, primary_key=True)
    filing_id = Column(Integer, ForeignKey("filings.id"), index=True, unique=True, nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True, nullable=False)
    report_date = Column(DateTime, index=True, nullable=False)
    content = Column(Text, nullable=False)

    # Relationships
    filing = relationship("Filing", back_populates="management_discussion")
    company = relationship("Company")

    def __repr__(self):
        return f"<ManagementDiscussion(filing_id={self.filing_id}, company_id={self.company_id})>"

    def to_dict(self):
        """Convert ManagementDiscussion object to dictionary"""
        result = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        return result

    def to_json(self):
        """Convert ManagementDiscussion object to JSON string"""
        import json
        return json.dumps(self.to_dict(), default=str)