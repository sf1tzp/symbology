"""Database model for per-user company watchlists.

The watchlist lives in `public` and is owned by Alembic. Rows are written and
read by the SvelteKit UI (via Kysely); the Python services don't use it yet.
This model exists so Alembic autogenerate recognises the table (and its
cross-schema FK to Better Auth's `auth."user"`) and never drops it.

The `user_id` FK references `auth."user"(id)`, which is created and owned by
`@better-auth/cli migrate`, not by SQLAlchemy. The string ForeignKey resolves
lazily, so the referent table does not need to be mapped here.
"""
from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, func, Text, text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from symbology.database.base import Base


class Watchlist(Base):
    """A single (user, company) star on a user's watchlist."""

    __tablename__ = "watchlist"
    __table_args__ = (
        UniqueConstraint("user_id", "company_id", name="uq_watchlist_user_company"),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[str] = mapped_column(
        Text, ForeignKey("auth.user.id", ondelete="CASCADE"), nullable=False, index=True
    )
    company_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<Watchlist(user_id={self.user_id!r}, company_id={self.company_id})>"
