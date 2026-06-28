"""Database model for supporter grants (the patronage ledger).

`supporter_grants` lives in `public` and is owned by Alembic. Each row is one
completed payment that grants the user some number of supporter days. Rows are
written by the SvelteKit UI's Stripe webhook and read back via Kysely; the
Python services don't use it yet. This model exists so Alembic autogenerate
recognises the table (and its cross-schema FK to Better Auth's `auth."user"`)
and never drops it.

The `user_id` FK references `auth."user"(id)`, created and owned by
`@better-auth/cli migrate`, not by SQLAlchemy. The string ForeignKey resolves
lazily, so the referent table does not need to be mapped here.
"""
from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, func, Integer, Text, text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from symbology.database.base import Base


class SupporterGrant(Base):
    """A single supporter purchase grant."""

    __tablename__ = "supporter_grants"
    __table_args__ = (
        UniqueConstraint("provider_txn_id", name="uq_supporter_grants_provider_txn_id"),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[str] = mapped_column(
        Text, ForeignKey("auth.user.id", ondelete="CASCADE"), nullable=False, index=True
    )
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    days: Mapped[int] = mapped_column(Integer, nullable=False)
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    provider_txn_id: Mapped[str] = mapped_column(Text, nullable=False)
    plan_type: Mapped[str] = mapped_column(Text, nullable=False)

    def __repr__(self) -> str:
        return (
            f"<SupporterGrant(user_id={self.user_id!r}, days={self.days}, "
            f"expires_at={self.expires_at!r})>"
        )
