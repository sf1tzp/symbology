from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Table,
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
    filings = relationship("Filing", back_populates="company", cascade="all, delete-orphan")
    # Relationship with balance sheet values
    balance_sheet_values = relationship("BalanceSheetValue", back_populates="company", cascade="all, delete-orphan")
    # Relationship with income statement values
    income_statement_values = relationship("IncomeStatementValue", back_populates="company", cascade="all, delete-orphan")
    # Relationship with cash flow statement values
    cash_flow_statement_values = relationship("CashFlowStatementValue", back_populates="company", cascade="all, delete-orphan")
    # Relationship with cover page values
    cover_page_values = relationship("CoverPageValue", back_populates="company", cascade="all, delete-orphan")

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
    balance_sheet_values = relationship("BalanceSheetValue", back_populates="filing", cascade="all, delete-orphan")
    # Relationship with income statement values
    income_statement_values = relationship("IncomeStatementValue", back_populates="filing", cascade="all, delete-orphan")
    # Relationship with cash flow statement values
    cash_flow_statement_values = relationship("CashFlowStatementValue", back_populates="filing", cascade="all, delete-orphan")
    # Relationship with cover page values
    cover_page_values = relationship("CoverPageValue", back_populates="filing", cascade="all, delete-orphan")
    # Relationship with source documents
    source_documents = relationship("SourceDocument", back_populates="filing", cascade="all, delete-orphan")

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


# Association table for AICompletion to SourceDocument many-to-many relationship
completion_source_documents = Table(
    "completion_source_documents",
    Base.metadata,
    Column("completion_id", Integer, ForeignKey("ai_completions.id"), primary_key=True),
    Column("source_document_id", Integer, ForeignKey("source_documents.id"), primary_key=True),
)

# Association table for AICompletion to AICompletion many-to-many self-referential relationship
completion_context_completions = Table(
    "completion_context_completions",
    Base.metadata,
    Column("parent_completion_id", Integer, ForeignKey("ai_completions.id"), primary_key=True),
    Column("context_completion_id", Integer, ForeignKey("ai_completions.id"), primary_key=True),
)

class SourceDocument(Base):
    """Model for storing source documents related to filings."""
    __tablename__ = "source_documents"

    id = Column(Integer, primary_key=True)
    filing_id = Column(Integer, ForeignKey("filings.id"), index=True, nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True, nullable=False)
    report_date = Column(DateTime, index=True, nullable=False)
    document_type = Column(String(100), index=True)  # Type of document (e.g., "exhibit", "attachment")
    document_name = Column(String(255))  # Name of the document
    content = Column(Text, nullable=False)
    url = Column(String(255))  # URL to the original document if available

    # Relationships
    filing = relationship("Filing", back_populates="source_documents")
    company = relationship("Company")

    # Relationship with AICompletions that use this document as context
    completions = relationship(
        "AICompletion",
        secondary=completion_source_documents,
        back_populates="source_documents"
    )

    def __repr__(self):
        return f"<SourceDocument(filing_id={self.filing_id}, document_type='{self.document_type}', document_name='{self.document_name}')>"

    def to_dict(self):
        """Convert SourceDocument object to dictionary"""
        result = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        return result

    def to_json(self):
        """Convert SourceDocument object to JSON string"""
        import json
        return json.dumps(self.to_dict(), default=str)


class PromptTemplate(Base):
    """Model for storing customizable prompt templates."""
    __tablename__ = "prompt_templates"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text)
    system_prompt = Column(Text, nullable=False)
    user_prompt_template = Column(Text, nullable=False)
    assistant_prompt_template = Column(Text)
    category = Column(String(50), index=True)  # e.g., "risk_analysis", "financial_position", "management_assessment"
    default_parameters = Column(JSON)  # Default query parameters like temperature, max_tokens
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)

    # Relationship with completions
    completions = relationship("AICompletion", back_populates="prompt_template", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<PromptTemplate(id={self.id}, name='{self.name}')>"

    def to_dict(self):
        """Convert PromptTemplate object to dictionary"""
        result = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        return result

    def to_json(self):
        """Convert PromptTemplate object to JSON string"""
        import json
        return json.dumps(self.to_dict(), default=str)


class AICompletion(Base):
    """Model for storing AI completions generated by OpenAI."""
    __tablename__ = "ai_completions"

    id = Column(Integer, primary_key=True)
    prompt_template_id = Column(Integer, ForeignKey("prompt_templates.id"), index=True, nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True)
    filing_id = Column(Integer, ForeignKey("filings.id"), index=True)

    # Removing the source_document_id field since we now use the many-to-many relationship
    # source_document_id = Column(Integer, ForeignKey("source_documents.id"), index=True)

    # Full prompts as sent to OpenAI (after template interpolation)
    system_prompt = Column(Text, nullable=False)
    user_prompt = Column(Text, nullable=False)
    context_texts = Column(JSON)  # List of context texts provided

    # OpenAI request parameters
    model = Column(String(100), nullable=False)
    temperature = Column(Float, nullable=False)
    max_tokens = Column(Integer, nullable=False)
    top_p = Column(Float)
    frequency_penalty = Column(Float)
    presence_penalty = Column(Float)
    stop_sequences = Column(JSON)  # List of stop sequences

    # Response data
    completion_text = Column(Text, nullable=False)
    completion_id = Column(String(100))  # OpenAI completion ID
    created_at = Column(DateTime, nullable=False)
    token_usage = Column(JSON)  # Token usage statistics

    # Analysis metadata
    tags = Column(JSON)  # User-defined tags for categorizing completions
    notes = Column(Text)  # Additional notes about this completion

    # Relationships
    prompt_template = relationship("PromptTemplate", back_populates="completions")
    company = relationship("Company")
    filing = relationship("Filing")

    # Many-to-many relationship with source documents used as context
    source_documents = relationship(
        "SourceDocument",
        secondary=completion_source_documents,
        back_populates="completions"
    )

    # Self-referential many-to-many relationship
    # Completions used as context for this completion (parent completions)
    context_completions = relationship(
        "AICompletion",
        secondary=completion_context_completions,
        primaryjoin=(completion_context_completions.c.parent_completion_id == id),
        secondaryjoin=(completion_context_completions.c.context_completion_id == id),
        backref="used_as_context_by"  # Completions that use this one as context (child completions)
    )

    ratings = relationship("CompletionRating", back_populates="completion", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<AICompletion(id={self.id}, prompt_template_id={self.prompt_template_id}, created_at={self.created_at})>"

    def to_dict(self):
        """Convert AICompletion object to dictionary"""
        result = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        return result

    def to_json(self):
        """Convert AICompletion object to JSON string"""
        import json
        return json.dumps(self.to_dict(), default=str)


class CompletionRating(Base):
    """Model for storing user ratings and comments on generated completions."""
    __tablename__ = "completion_ratings"

    id = Column(Integer, primary_key=True)
    completion_id = Column(Integer, ForeignKey("ai_completions.id"), index=True, nullable=False)
    rating = Column(Integer)  # e.g., 1-5 star rating
    accuracy_score = Column(Integer)  # How accurate the information is (1-5)
    relevance_score = Column(Integer)  # How relevant the completion is to the prompt (1-5)
    helpfulness_score = Column(Integer)  # How helpful the completion is (1-5)
    comments = Column(Text)  # User comments about the completion
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    # Relationship with completion
    completion = relationship("AICompletion", back_populates="ratings")

    def __repr__(self):
        return f"<CompletionRating(id={self.id}, completion_id={self.completion_id}, rating={self.rating})>"

    def to_dict(self):
        """Convert CompletionRating object to dictionary"""
        result = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        return result

    def to_json(self):
        """Convert CompletionRating object to JSON string"""
        import json
        return json.dumps(self.to_dict(), default=str)