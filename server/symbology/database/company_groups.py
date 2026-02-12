"""Database models and CRUD functions for company groups."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import Column, DateTime, ForeignKey, func, String, Table, Text
from sqlalchemy.dialects.postgresql import ARRAY, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship
from symbology.database.base import Base, get_db_session
from symbology.database.companies import Company
from symbology.utils.logging import get_logger
from uuid_extensions import uuid7

logger = get_logger(__name__)


# Association table for many-to-many relationship between CompanyGroup and Company
company_group_membership = Table(
    "company_group_membership",
    Base.metadata,
    Column("company_group_id", ForeignKey("company_groups.id", ondelete="CASCADE"), primary_key=True),
    Column("company_id", ForeignKey("companies.id", ondelete="CASCADE"), primary_key=True),
    Column("added_at", DateTime, default=func.now()),
)


class CompanyGroup(Base):
    """CompanyGroup model representing a reusable set of companies."""

    __tablename__ = "company_groups"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sic_codes: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    search_vector = mapped_column(TSVECTOR, nullable=True)

    companies: Mapped[List["Company"]] = relationship(
        "Company",
        secondary=company_group_membership,
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<CompanyGroup(id={self.id}, name='{self.name}', slug='{self.slug}')>"


# ---------------------------------------------------------------------------
# CRUD functions
# ---------------------------------------------------------------------------

def create_company_group(data: Dict[str, Any]) -> CompanyGroup:
    """Create a new company group."""
    try:
        session = get_db_session()
        group = CompanyGroup(**data)
        session.add(group)
        session.commit()
        logger.info("created_company_group", group_id=str(group.id), slug=group.slug)
        return group
    except Exception as e:
        session.rollback()
        logger.error("create_company_group_failed", error=str(e), exc_info=True)
        raise


def get_company_group_by_slug(slug: str) -> Optional[CompanyGroup]:
    """Get a company group by its slug."""
    try:
        session = get_db_session()
        group = session.query(CompanyGroup).filter(CompanyGroup.slug == slug).first()
        if group:
            logger.info("retrieved_company_group", slug=slug)
        else:
            logger.warning("company_group_not_found", slug=slug)
        return group
    except Exception as e:
        logger.error("get_company_group_by_slug_failed", slug=slug, error=str(e), exc_info=True)
        raise


def list_company_groups(
    limit: int = 50,
    offset: int = 0,
) -> List[CompanyGroup]:
    """List company groups."""
    try:
        session = get_db_session()
        query = session.query(CompanyGroup)
        query = query.order_by(CompanyGroup.name)
        groups = query.offset(offset).limit(limit).all()
        logger.info("listed_company_groups", count=len(groups))
        return groups
    except Exception as e:
        logger.error("list_company_groups_failed", error=str(e), exc_info=True)
        raise


def add_company_to_group(group_slug: str, company_id: UUID) -> bool:
    """Add a company to a group. Returns True if added, False if already a member."""
    try:
        session = get_db_session()
        group = get_company_group_by_slug(group_slug)
        if not group:
            raise ValueError(f"Company group not found: {group_slug}")

        company = session.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise ValueError(f"Company not found: {company_id}")

        if company in group.companies:
            logger.info("company_already_in_group", slug=group_slug, company_id=str(company_id))
            return False

        group.companies.append(company)
        session.commit()
        logger.info("added_company_to_group", slug=group_slug, company_id=str(company_id))
        return True
    except Exception as e:
        session.rollback()
        logger.error("add_company_to_group_failed", slug=group_slug, error=str(e), exc_info=True)
        raise


def remove_company_from_group(group_slug: str, company_id: UUID) -> bool:
    """Remove a company from a group. Returns True if removed, False if not a member."""
    try:
        session = get_db_session()
        group = get_company_group_by_slug(group_slug)
        if not group:
            raise ValueError(f"Company group not found: {group_slug}")

        company = session.query(Company).filter(Company.id == company_id).first()
        if not company or company not in group.companies:
            logger.warning("company_not_in_group", slug=group_slug, company_id=str(company_id))
            return False

        group.companies.remove(company)
        session.commit()
        logger.info("removed_company_from_group", slug=group_slug, company_id=str(company_id))
        return True
    except Exception as e:
        session.rollback()
        logger.error("remove_company_from_group_failed", slug=group_slug, error=str(e), exc_info=True)
        raise


def populate_group_from_sic_codes(group_slug: str) -> int:
    """Auto-populate a group by matching companies against the group's SIC codes.

    Returns the number of companies added.
    """
    try:
        session = get_db_session()
        group = get_company_group_by_slug(group_slug)
        if not group:
            raise ValueError(f"Company group not found: {group_slug}")

        if not group.sic_codes:
            logger.warning("no_sic_codes_for_group", slug=group_slug)
            return 0

        added = 0
        for sic_code in group.sic_codes:
            companies = (
                session.query(Company)
                .filter(Company.sic.like(f"{sic_code}%"))
                .all()
            )
            for company in companies:
                if company not in group.companies:
                    group.companies.append(company)
                    added += 1

        session.commit()
        logger.info("populated_group_from_sic_codes", slug=group_slug, added=added)
        return added
    except Exception as e:
        session.rollback()
        logger.error("populate_group_from_sic_codes_failed", slug=group_slug, error=str(e), exc_info=True)
        raise
