"""normalize enum values to lowercase

Revision ID: b2c3d4e56f7a
Revises: a1b2c3d45e6f
Create Date: 2026-02-13 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e56f7a'
down_revision: Union[str, None] = 'a1b2c3d45e6f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Enums to normalize: (enum_name, table, column, old_values -> new_values)
# content_stage_enum is already lowercase and skipped.
ENUM_MIGRATIONS = [
    {
        "name": "document_type_enum",
        "tables": [
            ("generated_content", "document_type"),
            ("documents", "document_type"),
        ],
        "mapping": {
            "MDA": "management_discussion",
            "RISK_FACTORS": "risk_factors",
            "DESCRIPTION": "business_description",
            "CONTROLS_PROCEDURES": "controls_procedures",
            "LEGAL_PROCEEDINGS": "legal_proceedings",
            "MARKET_RISK": "market_risk",
            "EXECUTIVE_COMPENSATION": "executive_compensation",
            "DIRECTORS_OFFICERS": "directors_officers",
        },
    },
    {
        "name": "content_source_type_enum",
        "tables": [("generated_content", "source_type")],
        "mapping": {
            "DOCUMENTS": "documents",
            "GENERATED_CONTENT": "generated_content",
            "BOTH": "both",
        },
    },
    {
        "name": "job_type_enum",
        "tables": [("jobs", "job_type")],
        "mapping": {
            "COMPANY_INGESTION": "company_ingestion",
            "FILING_INGESTION": "filing_ingestion",
            "CONTENT_GENERATION": "content_generation",
            "INGEST_PIPELINE": "ingest_pipeline",
            "FULL_PIPELINE": "full_pipeline",
            "BULK_INGEST": "bulk_ingest",
            "TEST": "test",
            # company_group_pipeline is already lowercase
        },
    },
    {
        "name": "job_status_enum",
        "tables": [("jobs", "status")],
        "mapping": {
            "PENDING": "pending",
            "IN_PROGRESS": "in_progress",
            "COMPLETED": "completed",
            "FAILED": "failed",
            "CANCELLED": "cancelled",
        },
    },
    {
        "name": "pipeline_trigger_enum",
        "tables": [("pipeline_runs", "trigger")],
        "mapping": {
            "MANUAL": "manual",
            "SCHEDULED": "scheduled",
        },
    },
    {
        "name": "pipeline_run_status_enum",
        "tables": [("pipeline_runs", "status")],
        "mapping": {
            "PENDING": "pending",
            "RUNNING": "running",
            "COMPLETED": "completed",
            "FAILED": "failed",
            "PARTIAL": "partial",
        },
    },
]


def upgrade() -> None:
    """Normalize all enum values from UPPERCASE to lowercase.

    Strategy: cast columns to text, drop old enum, create new enum with
    lowercase values, cast columns back. This handles the casing mismatch
    between early migrations (uppercase) and newer ones (lowercase).
    """
    for enum_def in ENUM_MIGRATIONS:
        name = enum_def["name"]
        mapping = enum_def["mapping"]
        tables = enum_def["tables"]
        old_name = f"{name}_old"

        # 1. Cast all columns from enum to text
        for table, column in tables:
            op.execute(f'ALTER TABLE {table} ALTER COLUMN "{column}" TYPE text USING "{column}"::text')

        # 2. Rename old enum
        op.execute(f"ALTER TYPE {name} RENAME TO {old_name}")

        # 3. Collect new values: mapped lowercase values + any already-lowercase values
        new_values = list(mapping.values())
        # For job_type_enum, include company_group_pipeline which is already lowercase
        if name == "job_type_enum":
            new_values.append("company_group_pipeline")
        quoted = ", ".join(f"'{v}'" for v in new_values)
        op.execute(f"CREATE TYPE {name} AS ENUM ({quoted})")

        # 4. Update existing data from uppercase to lowercase
        for table, column in tables:
            for old_val, new_val in mapping.items():
                op.execute(
                    f"UPDATE {table} SET \"{column}\" = '{new_val}' "
                    f"WHERE \"{column}\" = '{old_val}'"
                )

        # 5. Cast columns back to the new enum
        for table, column in tables:
            op.execute(
                f'ALTER TABLE {table} ALTER COLUMN "{column}" '
                f"TYPE {name} USING \"{column}\"::{name}"
            )

        # 6. Drop old enum
        op.execute(f"DROP TYPE {old_name}")


def downgrade() -> None:
    """Revert enum values from lowercase back to UPPERCASE."""
    for enum_def in ENUM_MIGRATIONS:
        name = enum_def["name"]
        mapping = enum_def["mapping"]
        tables = enum_def["tables"]
        old_name = f"{name}_old"

        # Reverse mapping: lowercase -> UPPERCASE
        reverse_mapping = {v: k for k, v in mapping.items()}

        # 1. Cast columns to text
        for table, column in tables:
            op.execute(f'ALTER TABLE {table} ALTER COLUMN "{column}" TYPE text USING "{column}"::text')

        # 2. Rename current enum
        op.execute(f"ALTER TYPE {name} RENAME TO {old_name}")

        # 3. Recreate with original uppercase values
        old_values = list(mapping.keys())
        if name == "job_type_enum":
            old_values.append("company_group_pipeline")
        quoted = ", ".join(f"'{v}'" for v in old_values)
        op.execute(f"CREATE TYPE {name} AS ENUM ({quoted})")

        # 4. Update data back to uppercase
        for table, column in tables:
            for new_val, old_val in reverse_mapping.items():
                op.execute(
                    f"UPDATE {table} SET \"{column}\" = '{old_val}' "
                    f"WHERE \"{column}\" = '{new_val}'"
                )

        # 5. Cast back
        for table, column in tables:
            op.execute(
                f'ALTER TABLE {table} ALTER COLUMN "{column}" '
                f"TYPE {name} USING \"{column}\"::{name}"
            )

        # 6. Drop old
        op.execute(f"DROP TYPE {old_name}")
