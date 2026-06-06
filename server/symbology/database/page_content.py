"""Page-content publishing layer.

A versioned, curated manifest of which immutable ``GeneratedContent`` pieces
compose each page. A ``*_page_content_pipeline`` run inserts a new immutable
row; "current" = the latest row per scope by ``created_at`` (history retained
for rollback/audit). Separate tables per page type so each can evolve
independently.

Conventions:
- Scope FK (the entity the page is about): ``ondelete CASCADE`` — page versions
  are meaningless once the entity is gone.
- Content-slot FKs -> generated_content: ``ondelete RESTRICT`` — a published
  snapshot must not dangle.
- Provenance is modeled relationally as M2M to *domain* entities.
"""
from datetime import datetime
from typing import Dict, List, Optional, TYPE_CHECKING, Union
from uuid import UUID

from sqlalchemy import Column, DateTime, Enum as SQLEnum, ForeignKey, func, Index, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship
from symbology.database.base import Base, get_db_session
from symbology.database.documents import DocumentType
from symbology.utils.logging import get_logger
from uuid_extensions import uuid7

if TYPE_CHECKING:
    from symbology.database.companies import Company
    from symbology.database.documents import Document
    from symbology.database.filings import Filing
    from symbology.database.generated_content import GeneratedContent

logger = get_logger(__name__)


# --- Provenance association tables (M2M to domain entities) ---------------

filing_page_content_document = Table(
    "filing_page_content_document",
    Base.metadata,
    Column("filing_page_content_id", ForeignKey("filing_page_content.id", ondelete="CASCADE"), primary_key=True),
    Column("document_id", ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True),
)

company_page_content_filing = Table(
    "company_page_content_filing",
    Base.metadata,
    Column("company_page_content_id", ForeignKey("company_page_content.id", ondelete="CASCADE"), primary_key=True),
    Column("filing_id", ForeignKey("filings.id", ondelete="CASCADE"), primary_key=True),
)

group_page_content_company = Table(
    "group_page_content_company",
    Base.metadata,
    Column("group_page_content_id", ForeignKey("group_page_content.id", ondelete="CASCADE"), primary_key=True),
    Column("company_id", ForeignKey("companies.id", ondelete="CASCADE"), primary_key=True),
)


# --- Page-content tables --------------------------------------------------

class DocumentPageContent(Base):
    """A published version of a document page (its L1 summary + intro)."""

    __tablename__ = "document_page_content"
    __table_args__ = (Index("ix_document_page_content_scope", "document_id", "created_at"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    document_id: Mapped[UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    summary_content_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("generated_content.id", ondelete="RESTRICT"), nullable=True
    )
    intro_content_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("generated_content.id", ondelete="RESTRICT"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    document: Mapped["Document"] = relationship("Document", foreign_keys=[document_id])
    summary_content: Mapped[Optional["GeneratedContent"]] = relationship(
        "GeneratedContent", foreign_keys=[summary_content_id]
    )
    intro_content: Mapped[Optional["GeneratedContent"]] = relationship(
        "GeneratedContent", foreign_keys=[intro_content_id]
    )


class FilingPageContent(Base):
    """A published version of a filing page (main content + intro)."""

    __tablename__ = "filing_page_content"
    __table_args__ = (Index("ix_filing_page_content_scope", "filing_id", "created_at"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    filing_id: Mapped[UUID] = mapped_column(ForeignKey("filings.id", ondelete="CASCADE"), nullable=False)
    main_content_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("generated_content.id", ondelete="RESTRICT"), nullable=True
    )
    intro_content_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("generated_content.id", ondelete="RESTRICT"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    filing: Mapped["Filing"] = relationship("Filing", foreign_keys=[filing_id])
    main_content: Mapped[Optional["GeneratedContent"]] = relationship(
        "GeneratedContent", foreign_keys=[main_content_id]
    )
    intro_content: Mapped[Optional["GeneratedContent"]] = relationship(
        "GeneratedContent", foreign_keys=[intro_content_id]
    )
    source_documents: Mapped[List["Document"]] = relationship(
        "Document", secondary=filing_page_content_document, lazy="selectin"
    )


class CompanyPageContent(Base):
    """A published version of a company page (main + intro + change reports)."""

    __tablename__ = "company_page_content"
    __table_args__ = (
        Index("ix_company_page_content_scope", "company_id", "created_at"),
        Index("ix_company_page_content_scope_form", "company_id", "form", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    # The filing form this page was synthesised from (e.g. "10-K", "10-Q"); a
    # company publishes one current page per form and the UI fetches by form.
    form: Mapped[str] = mapped_column(String(10), nullable=False)
    main_content_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("generated_content.id", ondelete="RESTRICT"), nullable=True
    )
    intro_content_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("generated_content.id", ondelete="RESTRICT"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    company: Mapped["Company"] = relationship("Company", foreign_keys=[company_id])
    main_content: Mapped[Optional["GeneratedContent"]] = relationship(
        "GeneratedContent", foreign_keys=[main_content_id]
    )
    intro_content: Mapped[Optional["GeneratedContent"]] = relationship(
        "GeneratedContent", foreign_keys=[intro_content_id]
    )
    source_filings: Mapped[List["Filing"]] = relationship(
        "Filing", secondary=company_page_content_filing, lazy="selectin"
    )
    change_reports: Mapped[List["CompanyPageContentChangeReport"]] = relationship(
        "CompanyPageContentChangeReport",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class CompanyPageContentChangeReport(Base):
    """Per-document-type change report (and its intro) on a company page version."""

    __tablename__ = "company_page_content_change_report"

    company_page_content_id: Mapped[UUID] = mapped_column(
        ForeignKey("company_page_content.id", ondelete="CASCADE"), primary_key=True
    )
    document_type: Mapped[DocumentType] = mapped_column(
        SQLEnum(DocumentType, name="document_type_enum", values_callable=lambda obj: [e.value for e in obj]),
        primary_key=True,
    )
    change_report_id: Mapped[UUID] = mapped_column(
        ForeignKey("generated_content.id", ondelete="RESTRICT"), nullable=False
    )
    change_report_intro_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("generated_content.id", ondelete="RESTRICT"), nullable=True
    )

    change_report: Mapped["GeneratedContent"] = relationship(
        "GeneratedContent", foreign_keys=[change_report_id]
    )
    change_report_intro: Mapped[Optional["GeneratedContent"]] = relationship(
        "GeneratedContent", foreign_keys=[change_report_intro_id]
    )


class GroupPageContent(Base):
    """A published version of a group page (main + intro + member companies)."""

    __tablename__ = "group_page_content"
    __table_args__ = (Index("ix_group_page_content_scope", "company_group_id", "created_at"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    company_group_id: Mapped[UUID] = mapped_column(
        ForeignKey("company_groups.id", ondelete="CASCADE"), nullable=False
    )
    main_content_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("generated_content.id", ondelete="RESTRICT"), nullable=True
    )
    intro_content_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("generated_content.id", ondelete="RESTRICT"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    main_content: Mapped[Optional["GeneratedContent"]] = relationship(
        "GeneratedContent", foreign_keys=[main_content_id]
    )
    intro_content: Mapped[Optional["GeneratedContent"]] = relationship(
        "GeneratedContent", foreign_keys=[intro_content_id]
    )
    member_companies: Mapped[List["Company"]] = relationship(
        "Company", secondary=group_page_content_company, lazy="selectin"
    )


# --- Publish helpers (the assembly side) ----------------------------------

def _content_id(content_hash: Optional[str]) -> Optional[UUID]:
    """Resolve a content hash to a GeneratedContent id (None if missing)."""
    if not content_hash:
        return None
    from symbology.database.generated_content import get_generated_content_by_hash
    gc = get_generated_content_by_hash(content_hash)
    return gc.id if gc else None


def publish_document_page_content(
    document_id: Union[UUID, str],
    summary_hash: Optional[str] = None,
    intro_hash: Optional[str] = None,
) -> DocumentPageContent:
    """Insert a new immutable DocumentPageContent version from content hashes."""
    session = get_db_session()
    page = DocumentPageContent(
        document_id=document_id,
        summary_content_id=_content_id(summary_hash),
        intro_content_id=_content_id(intro_hash),
    )
    session.add(page)
    session.commit()
    logger.info("published_document_page_content", document_id=str(document_id), page_id=str(page.id))
    return page


def publish_company_page_content(
    company_id: Union[UUID, str],
    form: str,
    main_hash: Optional[str] = None,
    intro_hash: Optional[str] = None,
    change_reports: Optional[Dict[Union["DocumentType", str], tuple]] = None,
    source_filing_ids: Optional[List[UUID]] = None,
) -> "CompanyPageContent":
    """Insert a new immutable CompanyPageContent version.

    ``form`` is the filing form the page was synthesised from (e.g. "10-K",
    "10-Q"); a company keeps one current page per form.
    ``change_reports`` maps a document type (``DocumentType`` or its value) to a
    ``(change_report_hash, change_report_intro_hash)`` tuple; the intro hash may
    be ``None``. ``source_filing_ids`` records the filings the page was derived
    from (M2M provenance).
    """
    session = get_db_session()
    page = CompanyPageContent(
        company_id=company_id,
        form=form,
        main_content_id=_content_id(main_hash),
        intro_content_id=_content_id(intro_hash),
    )
    for doc_type, hashes in (change_reports or {}).items():
        report_hash, intro = hashes if isinstance(hashes, tuple) else (hashes, None)
        report_id = _content_id(report_hash)
        if report_id is None:
            continue  # the report slot is required — skip a doc type we couldn't resolve
        page.change_reports.append(
            CompanyPageContentChangeReport(
                document_type=DocumentType(doc_type) if isinstance(doc_type, str) else doc_type,
                change_report_id=report_id,
                change_report_intro_id=_content_id(intro),
            )
        )
    if source_filing_ids:
        from symbology.database.filings import Filing
        page.source_filings = (
            session.query(Filing).filter(Filing.id.in_(source_filing_ids)).all()
        )
    session.add(page)
    session.commit()
    logger.info(
        "published_company_page_content",
        company_id=str(company_id),
        form=form,
        page_id=str(page.id),
        change_reports=len(page.change_reports),
    )
    return page


def publish_filing_page_content(
    filing_id: Union[UUID, str],
    main_hash: Optional[str] = None,
    intro_hash: Optional[str] = None,
    source_document_ids: Optional[List[UUID]] = None,
) -> FilingPageContent:
    """Insert a new immutable FilingPageContent version + source-document provenance."""
    session = get_db_session()
    page = FilingPageContent(
        filing_id=filing_id,
        main_content_id=_content_id(main_hash),
        intro_content_id=_content_id(intro_hash),
    )
    if source_document_ids:
        from symbology.database.documents import Document
        page.source_documents = (
            session.query(Document).filter(Document.id.in_(source_document_ids)).all()
        )
    session.add(page)
    session.commit()
    logger.info("published_filing_page_content", filing_id=str(filing_id), page_id=str(page.id))
    return page


# --- Read helpers (the render path) ---------------------------------------

def get_current_document_page_content(document_id: Union[UUID, str]) -> Optional[DocumentPageContent]:
    """The latest published document page version for a document."""
    session = get_db_session()
    return (
        session.query(DocumentPageContent)
        .filter(DocumentPageContent.document_id == document_id)
        .order_by(DocumentPageContent.created_at.desc())
        .first()
    )


def get_current_filing_page_content(filing_id: Union[UUID, str]) -> Optional[FilingPageContent]:
    """The latest published filing page version for a filing."""
    session = get_db_session()
    return (
        session.query(FilingPageContent)
        .filter(FilingPageContent.filing_id == filing_id)
        .order_by(FilingPageContent.created_at.desc())
        .first()
    )


def get_current_company_page_content(
    company_id: Union[UUID, str], form: Optional[str] = None
) -> Optional[CompanyPageContent]:
    """The latest published company page version for a company.

    When ``form`` is given, returns the latest page synthesised from that filing
    form (e.g. "10-Q"); otherwise the latest page of any form.
    """
    session = get_db_session()
    query = session.query(CompanyPageContent).filter(
        CompanyPageContent.company_id == company_id
    )
    if form is not None:
        query = query.filter(CompanyPageContent.form == form)
    return query.order_by(CompanyPageContent.created_at.desc()).first()


def get_current_group_page_content(company_group_id: Union[UUID, str]) -> Optional[GroupPageContent]:
    """The latest published group page version for a company group."""
    session = get_db_session()
    return (
        session.query(GroupPageContent)
        .filter(GroupPageContent.company_group_id == company_group_id)
        .order_by(GroupPageContent.created_at.desc())
        .first()
    )
