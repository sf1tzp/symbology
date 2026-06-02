"""Core sync engine for copying data between two Symbology databases.

Resolves all cross-DB references via natural keys (ticker, content_hash,
accession_number, slug, name) since UUID7 IDs differ between databases.
"""

import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import quote_plus
from uuid import UUID

from rich.console import Console
from rich.table import Table
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker, undefer

from symbology.database.companies import Company
from symbology.database.company_groups import CompanyGroup, company_group_membership
from symbology.database.documents import Document
from symbology.database.filings import Filing
from symbology.database.financial_concepts import FinancialConcept
from symbology.database.financial_values import FinancialValue
from symbology.database.generated_content import (
    GeneratedContent,
    generated_content_document_association,
    generated_content_source_association,
)
from symbology.database.model_configs import ModelConfig
from symbology.database.page_content import (
    CompanyPageContent,
    CompanyPageContentChangeReport,
    DocumentPageContent,
    FilingPageContent,
    GroupPageContent,
    company_page_content_filing,
    filing_page_content_document,
    group_page_content_company,
)
from symbology.database.prompts import Prompt
from symbology.utils.logging import get_logger
from uuid_extensions import uuid7

logger = get_logger(__name__)
console = Console()


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class SyncStats:
    table: str
    total_source: int = 0
    already_exists: int = 0
    synced: int = 0
    skipped_fk: int = 0
    errors: int = 0


@dataclass
class NaturalKeyMaps:
    """Lookup dicts mapping natural keys -> target UUIDs."""
    ticker_to_company_id: Dict[str, UUID] = field(default_factory=dict)
    slug_to_group_id: Dict[str, UUID] = field(default_factory=dict)
    accession_to_filing_id: Dict[str, UUID] = field(default_factory=dict)
    doc_hash_to_id: Dict[str, UUID] = field(default_factory=dict)
    concept_name_to_id: Dict[str, UUID] = field(default_factory=dict)
    prompt_hash_to_id: Dict[str, UUID] = field(default_factory=dict)
    mc_hash_to_id: Dict[str, UUID] = field(default_factory=dict)
    gc_hash_to_id: Dict[str, UUID] = field(default_factory=dict)
    # Page-content versions have no content_hash; identity is (scope natural
    # key, created_at). created_at is preserved on copy so the key is stable.
    doc_page_key_to_id: Dict[tuple, UUID] = field(default_factory=dict)
    filing_page_key_to_id: Dict[tuple, UUID] = field(default_factory=dict)
    company_page_key_to_id: Dict[tuple, UUID] = field(default_factory=dict)
    group_page_key_to_id: Dict[tuple, UUID] = field(default_factory=dict)
    # Direct source page id -> target page id, populated as page rows are
    # synced, so child/provenance tables (Phase 7) can resolve their parent.
    src_page_id_to_target: Dict[UUID, UUID] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Environment / connection helpers
# ---------------------------------------------------------------------------

def _project_root() -> Path:
    """Find the project root (parent of server/)."""
    # Walk up from this file: db_sync.py -> cli -> symbology -> server -> <root>
    return Path(__file__).resolve().parents[3]


def resolve_db_url(env_name: str) -> str:
    """Decrypt a sops-encrypted secrets/<env_name>.env and build a PostgreSQL URL."""
    secrets_path = _project_root() / "secrets" / f"{env_name}.env"
    if not secrets_path.exists():
        console.print(f"[red]Secrets file not found: {secrets_path}[/red]")
        sys.exit(1)

    try:
        result = subprocess.run(
            ["sops", "-d", str(secrets_path)],
            capture_output=True, text=True, check=True,
        )
    except FileNotFoundError:
        console.print("[red]sops not found. Ensure sops is on your PATH.[/red]")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        console.print(f"[red]sops decryption failed: {e.stderr.strip()}[/red]")
        sys.exit(1)

    env_vars: Dict[str, str] = {}
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env_vars[key.strip()] = value.strip()

    required = ["DATABASE_HOST", "DATABASE_PORT", "DATABASE_USER", "DATABASE_PASSWORD", "DATABASE_NAME"]
    missing = [k for k in required if k not in env_vars]
    if missing:
        console.print(f"[red]Missing vars in {secrets_path}: {', '.join(missing)}[/red]")
        sys.exit(1)

    password = quote_plus(env_vars["DATABASE_PASSWORD"])
    return (
        f"postgresql://{env_vars['DATABASE_USER']}:{password}"
        f"@{env_vars['DATABASE_HOST']}:{env_vars['DATABASE_PORT']}"
        f"/{env_vars['DATABASE_NAME']}"
    )


def create_session(db_url: str) -> Session:
    """Create an independent SQLAlchemy session (does not use init_db globals)."""
    engine = create_engine(db_url)
    factory = sessionmaker(bind=engine)
    return factory()


# ---------------------------------------------------------------------------
# Natural key map builder
# ---------------------------------------------------------------------------

def build_maps(target: Session) -> NaturalKeyMaps:
    """Build lookup dicts from the target database."""
    maps = NaturalKeyMaps()
    maps.ticker_to_company_id = {
        t: id for id, t in target.execute(select(Company.id, Company.ticker)).all()
    }
    maps.slug_to_group_id = {
        s: id for id, s in target.execute(select(CompanyGroup.id, CompanyGroup.slug)).all()
    }
    maps.accession_to_filing_id = {
        a: id for id, a in target.execute(select(Filing.id, Filing.accession_number)).all()
    }
    maps.doc_hash_to_id = {
        h: id for id, h in target.execute(
            select(Document.id, Document.content_hash).where(Document.content_hash.is_not(None))
        ).all()
    }
    maps.concept_name_to_id = {
        n: id for id, n in target.execute(select(FinancialConcept.id, FinancialConcept.name)).all()
    }
    maps.prompt_hash_to_id = {
        h: id for id, h in target.execute(
            select(Prompt.id, Prompt.content_hash).where(Prompt.content_hash.is_not(None))
        ).all()
    }
    maps.mc_hash_to_id = {
        h: id for id, h in target.execute(
            select(ModelConfig.id, ModelConfig.content_hash).where(ModelConfig.content_hash.is_not(None))
        ).all()
    }
    maps.gc_hash_to_id = {
        h: id for id, h in target.execute(
            select(GeneratedContent.id, GeneratedContent.content_hash)
            .where(GeneratedContent.content_hash.is_not(None))
        ).all()
    }
    # Page-content version keys: (scope natural key, created_at) -> page id.
    maps.doc_page_key_to_id = {
        (h, ca): pid for pid, h, ca in target.execute(
            select(DocumentPageContent.id, Document.content_hash, DocumentPageContent.created_at)
            .join(Document, DocumentPageContent.document_id == Document.id)
            .where(Document.content_hash.is_not(None))
        ).all()
    }
    maps.filing_page_key_to_id = {
        (a, ca): pid for pid, a, ca in target.execute(
            select(FilingPageContent.id, Filing.accession_number, FilingPageContent.created_at)
            .join(Filing, FilingPageContent.filing_id == Filing.id)
        ).all()
    }
    maps.company_page_key_to_id = {
        (t, ca): pid for pid, t, ca in target.execute(
            select(CompanyPageContent.id, Company.ticker, CompanyPageContent.created_at)
            .join(Company, CompanyPageContent.company_id == Company.id)
        ).all()
    }
    maps.group_page_key_to_id = {
        (s, ca): pid for pid, s, ca in target.execute(
            select(GroupPageContent.id, CompanyGroup.slug, GroupPageContent.created_at)
            .join(CompanyGroup, GroupPageContent.company_group_id == CompanyGroup.id)
        ).all()
    }
    return maps


# ---------------------------------------------------------------------------
# Source-side lookup helpers (natural key -> source natural key of FK target)
# ---------------------------------------------------------------------------

def _source_company_ticker(source: Session, company_id: UUID) -> Optional[str]:
    """Get ticker for a source company by its source UUID."""
    row = source.execute(select(Company.ticker).where(Company.id == company_id)).first()
    return row[0] if row else None


def _source_group_slug(source: Session, group_id: UUID) -> Optional[str]:
    row = source.execute(select(CompanyGroup.slug).where(CompanyGroup.id == group_id)).first()
    return row[0] if row else None


def _source_filing_accession(source: Session, filing_id: UUID) -> Optional[str]:
    row = source.execute(select(Filing.accession_number).where(Filing.id == filing_id)).first()
    return row[0] if row else None


def _source_prompt_hash(source: Session, prompt_id: UUID) -> Optional[str]:
    row = source.execute(select(Prompt.content_hash).where(Prompt.id == prompt_id)).first()
    return row[0] if row else None


def _source_mc_hash(source: Session, mc_id: UUID) -> Optional[str]:
    row = source.execute(select(ModelConfig.content_hash).where(ModelConfig.id == mc_id)).first()
    return row[0] if row else None


def _source_doc_hash(source: Session, doc_id: UUID) -> Optional[str]:
    row = source.execute(select(Document.content_hash).where(Document.id == doc_id)).first()
    return row[0] if row else None


def _source_gc_hash(source: Session, gc_id: UUID) -> Optional[str]:
    row = source.execute(select(GeneratedContent.content_hash).where(GeneratedContent.id == gc_id)).first()
    return row[0] if row else None


def _resolve_gc(source: Session, maps: NaturalKeyMaps, gc_id: Optional[UUID]) -> Optional[UUID]:
    """Resolve a source generated_content id to the target id via content_hash."""
    if not gc_id:
        return None
    h = _source_gc_hash(source, gc_id)
    return maps.gc_hash_to_id.get(h) if h else None


# ---------------------------------------------------------------------------
# Phase 1: tables with no FK dependencies
# ---------------------------------------------------------------------------

def sync_companies(source: Session, target: Session, dry_run: bool) -> SyncStats:
    stats = SyncStats(table="companies")
    source_rows = source.query(Company).all()
    stats.total_source = len(source_rows)

    existing_tickers = {t for (t,) in target.execute(select(Company.ticker)).all()}

    for row in source_rows:
        if row.ticker in existing_tickers:
            stats.already_exists += 1
            continue
        if dry_run:
            stats.synced += 1
            continue
        new = Company(
            id=uuid7(),
            name=row.name,
            display_name=row.display_name,
            ticker=row.ticker,
            exchanges=row.exchanges or [],
            sic=row.sic,
            cik=row.cik,
            sic_description=row.sic_description,
            fiscal_year_end=row.fiscal_year_end,
            former_names=row.former_names or [],
        )
        target.add(new)
        stats.synced += 1

    if not dry_run:
        target.commit()
    return stats


def sync_company_groups(source: Session, target: Session, dry_run: bool) -> SyncStats:
    stats = SyncStats(table="company_groups")
    source_rows = source.query(CompanyGroup).all()
    stats.total_source = len(source_rows)

    existing_slugs = {s for (s,) in target.execute(select(CompanyGroup.slug)).all()}

    for row in source_rows:
        if row.slug in existing_slugs:
            stats.already_exists += 1
            continue
        if dry_run:
            stats.synced += 1
            continue
        new = CompanyGroup(
            id=uuid7(),
            name=row.name,
            slug=row.slug,
            description=row.description,
            sic_codes=row.sic_codes or [],
        )
        target.add(new)
        stats.synced += 1

    if not dry_run:
        target.commit()
    return stats


def sync_financial_concepts(source: Session, target: Session, dry_run: bool) -> SyncStats:
    stats = SyncStats(table="financial_concepts")
    source_rows = source.query(FinancialConcept).all()
    stats.total_source = len(source_rows)

    existing_names = {n for (n,) in target.execute(select(FinancialConcept.name)).all()}

    for row in source_rows:
        if row.name in existing_names:
            stats.already_exists += 1
            continue
        if dry_run:
            stats.synced += 1
            continue
        new = FinancialConcept(
            id=uuid7(),
            name=row.name,
            description=row.description,
            labels=row.labels or [],
        )
        target.add(new)
        stats.synced += 1

    if not dry_run:
        target.commit()
    return stats


def sync_prompts(source: Session, target: Session, dry_run: bool) -> SyncStats:
    stats = SyncStats(table="prompts")
    source_rows = source.query(Prompt).all()
    stats.total_source = len(source_rows)

    existing_hashes = {h for (h,) in target.execute(
        select(Prompt.content_hash).where(Prompt.content_hash.is_not(None))
    ).all()}

    for row in source_rows:
        if row.content_hash and row.content_hash in existing_hashes:
            stats.already_exists += 1
            continue
        if dry_run:
            stats.synced += 1
            continue
        new = Prompt(
            id=uuid7(),
            name=row.name,
            description=row.description,
            role=row.role,
            content=row.content,
            content_hash=row.content_hash,
        )
        target.add(new)
        stats.synced += 1

    if not dry_run:
        target.commit()
    return stats


def sync_model_configs(source: Session, target: Session, dry_run: bool) -> SyncStats:
    stats = SyncStats(table="model_configs")
    source_rows = source.query(ModelConfig).all()
    stats.total_source = len(source_rows)

    existing_hashes = {h for (h,) in target.execute(
        select(ModelConfig.content_hash).where(ModelConfig.content_hash.is_not(None))
    ).all()}

    for row in source_rows:
        if row.content_hash and row.content_hash in existing_hashes:
            stats.already_exists += 1
            continue
        if dry_run:
            stats.synced += 1
            continue
        new = ModelConfig(
            id=uuid7(),
            model=row.model,
            options_json=row.options_json,
            content_hash=row.content_hash,
        )
        target.add(new)
        stats.synced += 1

    if not dry_run:
        target.commit()
    return stats


# ---------------------------------------------------------------------------
# Phase 2: FK → Phase 1
# ---------------------------------------------------------------------------

def sync_filings(source: Session, target: Session, maps: NaturalKeyMaps, dry_run: bool) -> SyncStats:
    stats = SyncStats(table="filings")
    source_rows = source.query(Filing).all()
    stats.total_source = len(source_rows)

    existing_accessions = {a for (a,) in target.execute(select(Filing.accession_number)).all()}

    for row in source_rows:
        if row.accession_number in existing_accessions:
            stats.already_exists += 1
            continue

        # Resolve company FK via ticker
        ticker = _source_company_ticker(source, row.company_id)
        target_company_id = maps.ticker_to_company_id.get(ticker) if ticker else None
        if not target_company_id:
            stats.skipped_fk += 1
            continue

        if dry_run:
            stats.synced += 1
            continue

        new = Filing(
            id=uuid7(),
            company_id=target_company_id,
            accession_number=row.accession_number,
            form=row.form,
            filing_date=row.filing_date,
            period_of_report=row.period_of_report,
            url=row.url,
        )
        target.add(new)
        stats.synced += 1

    if not dry_run:
        target.commit()
    return stats


def sync_group_membership(source: Session, target: Session, maps: NaturalKeyMaps, dry_run: bool) -> SyncStats:
    stats = SyncStats(table="company_group_membership")

    # Get all source memberships with their natural keys
    source_memberships = source.execute(
        select(
            CompanyGroup.slug,
            Company.ticker,
        )
        .select_from(company_group_membership)
        .join(CompanyGroup, company_group_membership.c.company_group_id == CompanyGroup.id)
        .join(Company, company_group_membership.c.company_id == Company.id)
    ).all()
    stats.total_source = len(source_memberships)

    # Get existing target memberships
    existing = set(target.execute(
        select(
            company_group_membership.c.company_group_id,
            company_group_membership.c.company_id,
        )
    ).all())

    for slug, ticker in source_memberships:
        target_group_id = maps.slug_to_group_id.get(slug)
        target_company_id = maps.ticker_to_company_id.get(ticker)

        if not target_group_id or not target_company_id:
            stats.skipped_fk += 1
            continue

        if (target_group_id, target_company_id) in existing:
            stats.already_exists += 1
            continue

        if dry_run:
            stats.synced += 1
            continue

        target.execute(
            company_group_membership.insert().values(
                company_group_id=target_group_id,
                company_id=target_company_id,
            )
        )
        stats.synced += 1

    if not dry_run:
        target.commit()
    return stats


# ---------------------------------------------------------------------------
# Phase 3: FK → Phase 1+2
# ---------------------------------------------------------------------------

def sync_documents(source: Session, target: Session, maps: NaturalKeyMaps, dry_run: bool) -> SyncStats:
    stats = SyncStats(table="documents")
    source_rows = source.query(Document).options(undefer(Document.content)).all()
    stats.total_source = len(source_rows)

    existing_hashes = {h for (h,) in target.execute(
        select(Document.content_hash).where(Document.content_hash.is_not(None))
    ).all()}

    for row in source_rows:
        if row.content_hash and row.content_hash in existing_hashes:
            stats.already_exists += 1
            continue

        # Resolve company FK
        ticker = _source_company_ticker(source, row.company_id)
        target_company_id = maps.ticker_to_company_id.get(ticker) if ticker else None
        if not target_company_id:
            stats.skipped_fk += 1
            continue

        # Resolve filing FK (optional)
        target_filing_id = None
        if row.filing_id:
            accession = _source_filing_accession(source, row.filing_id)
            target_filing_id = maps.accession_to_filing_id.get(accession) if accession else None

        if dry_run:
            stats.synced += 1
            continue

        new = Document(
            id=uuid7(),
            filing_id=target_filing_id,
            company_id=target_company_id,
            title=row.title,
            document_type=row.document_type,
            content=row.content,
            content_hash=row.content_hash,
        )
        target.add(new)
        stats.synced += 1

    if not dry_run:
        target.commit()
    return stats


# ---------------------------------------------------------------------------
# Phase 4: FK → Phase 1-3
# ---------------------------------------------------------------------------

def sync_financial_values(source: Session, target: Session, maps: NaturalKeyMaps, dry_run: bool) -> SyncStats:
    stats = SyncStats(table="financial_values")
    source_rows = source.query(FinancialValue).all()
    stats.total_source = len(source_rows)

    # Build composite keys for existing target values
    existing_composites = set()
    for fv in target.query(FinancialValue).all():
        ticker = None
        for t, cid in maps.ticker_to_company_id.items():
            if cid == fv.company_id:
                ticker = t
                break
        concept_name = None
        for n, cid in maps.concept_name_to_id.items():
            if cid == fv.concept_id:
                concept_name = n
                break
        if ticker and concept_name:
            existing_composites.add((ticker, concept_name, fv.value_date))

    for row in source_rows:
        # Resolve source natural keys
        ticker = _source_company_ticker(source, row.company_id)
        if not ticker:
            stats.skipped_fk += 1
            continue

        # Get concept name from source
        concept_row = source.execute(
            select(FinancialConcept.name).where(FinancialConcept.id == row.concept_id)
        ).first()
        concept_name = concept_row[0] if concept_row else None
        if not concept_name:
            stats.skipped_fk += 1
            continue

        # Dedup by composite key
        if (ticker, concept_name, row.value_date) in existing_composites:
            stats.already_exists += 1
            continue

        # Resolve target FKs
        target_company_id = maps.ticker_to_company_id.get(ticker)
        target_concept_id = maps.concept_name_to_id.get(concept_name)
        if not target_company_id or not target_concept_id:
            stats.skipped_fk += 1
            continue

        # Resolve filing FK (optional)
        target_filing_id = None
        if row.filing_id:
            accession = _source_filing_accession(source, row.filing_id)
            target_filing_id = maps.accession_to_filing_id.get(accession) if accession else None

        if dry_run:
            stats.synced += 1
            continue

        new = FinancialValue(
            id=uuid7(),
            company_id=target_company_id,
            concept_id=target_concept_id,
            filing_id=target_filing_id,
            value_date=row.value_date,
            value=row.value,
        )
        target.add(new)
        stats.synced += 1

    if not dry_run:
        target.commit()
    return stats


def sync_generated_content(source: Session, target: Session, maps: NaturalKeyMaps, dry_run: bool) -> SyncStats:
    stats = SyncStats(table="generated_content")
    source_rows = source.query(GeneratedContent).options(
        undefer(GeneratedContent.content),
    ).all()
    stats.total_source = len(source_rows)

    existing_hashes = set(maps.gc_hash_to_id.keys())

    for row in source_rows:
        if row.content_hash and row.content_hash in existing_hashes:
            stats.already_exists += 1
            continue

        # Resolve company FK (required for company-specific content)
        target_company_id = None
        if row.company_id:
            ticker = _source_company_ticker(source, row.company_id)
            target_company_id = maps.ticker_to_company_id.get(ticker) if ticker else None
            if not target_company_id:
                stats.skipped_fk += 1
                continue

        # Resolve company group FK (optional, null if missing)
        target_group_id = None
        if row.company_group_id:
            slug = _source_group_slug(source, row.company_group_id)
            target_group_id = maps.slug_to_group_id.get(slug) if slug else None

        # Resolve scope FKs (optional; SET NULL semantics, so null if missing)
        target_filing_id = None
        if row.filing_id:
            accession = _source_filing_accession(source, row.filing_id)
            target_filing_id = maps.accession_to_filing_id.get(accession) if accession else None

        target_document_id = None
        if row.document_id:
            d_hash = _source_doc_hash(source, row.document_id)
            target_document_id = maps.doc_hash_to_id.get(d_hash) if d_hash else None

        # Resolve prompt FKs
        target_sys_prompt_id = None
        if row.system_prompt_id:
            h = _source_prompt_hash(source, row.system_prompt_id)
            target_sys_prompt_id = maps.prompt_hash_to_id.get(h) if h else None

        target_user_prompt_id = None
        if row.user_prompt_id:
            h = _source_prompt_hash(source, row.user_prompt_id)
            target_user_prompt_id = maps.prompt_hash_to_id.get(h) if h else None

        # Resolve model config FK
        target_mc_id = None
        if row.model_config_id:
            h = _source_mc_hash(source, row.model_config_id)
            target_mc_id = maps.mc_hash_to_id.get(h) if h else None

        if dry_run:
            stats.synced += 1
            continue

        new_id = uuid7()
        new = GeneratedContent(
            id=new_id,
            content_hash=row.content_hash,
            company_id=target_company_id,
            company_group_id=target_group_id,
            filing_id=target_filing_id,
            document_id=target_document_id,
            generation_depth=row.generation_depth,
            description=row.description,
            document_type=row.document_type,
            form_type=row.form_type,
            content_stage=row.content_stage,
            source_type=row.source_type,
            created_at=row.created_at,
            total_duration=row.total_duration,
            input_tokens=row.input_tokens,
            output_tokens=row.output_tokens,
            warning=row.warning,
            content=row.content,
            summary=row.summary,
            model_config_id=target_mc_id,
            system_prompt_id=target_sys_prompt_id,
            user_prompt_id=target_user_prompt_id,
        )
        target.add(new)
        # Track for association sync
        maps.gc_hash_to_id[row.content_hash] = new_id
        stats.synced += 1

    if not dry_run:
        target.commit()
    return stats


# ---------------------------------------------------------------------------
# Phase 5: association tables
# ---------------------------------------------------------------------------

def sync_gc_document_associations(source: Session, target: Session, maps: NaturalKeyMaps, dry_run: bool) -> SyncStats:
    stats = SyncStats(table="gc_document_assoc")

    source_assocs = source.execute(
        select(
            generated_content_document_association.c.generated_content_id,
            generated_content_document_association.c.document_id,
        )
    ).all()
    stats.total_source = len(source_assocs)

    # Build existing target associations
    existing = set(target.execute(
        select(
            generated_content_document_association.c.generated_content_id,
            generated_content_document_association.c.document_id,
        )
    ).all())

    for src_gc_id, src_doc_id in source_assocs:
        # Resolve via natural keys
        gc_hash = _source_gc_hash(source, src_gc_id)
        doc_hash = _source_doc_hash(source, src_doc_id)

        target_gc_id = maps.gc_hash_to_id.get(gc_hash) if gc_hash else None
        target_doc_id = maps.doc_hash_to_id.get(doc_hash) if doc_hash else None

        if not target_gc_id or not target_doc_id:
            stats.skipped_fk += 1
            continue

        if (target_gc_id, target_doc_id) in existing:
            stats.already_exists += 1
            continue

        if dry_run:
            stats.synced += 1
            continue

        target.execute(
            generated_content_document_association.insert().values(
                generated_content_id=target_gc_id,
                document_id=target_doc_id,
            )
        )
        stats.synced += 1

    if not dry_run:
        target.commit()
    return stats


def sync_gc_source_associations(source: Session, target: Session, maps: NaturalKeyMaps, dry_run: bool) -> SyncStats:
    stats = SyncStats(table="gc_source_assoc")

    source_assocs = source.execute(
        select(
            generated_content_source_association.c.parent_content_id,
            generated_content_source_association.c.source_content_id,
            generated_content_source_association.c.relationship_type,
        )
    ).all()
    stats.total_source = len(source_assocs)

    existing = set(target.execute(
        select(
            generated_content_source_association.c.parent_content_id,
            generated_content_source_association.c.source_content_id,
        )
    ).all())

    for src_parent_id, src_source_id, rel_type in source_assocs:
        parent_hash = _source_gc_hash(source, src_parent_id)
        source_hash = _source_gc_hash(source, src_source_id)

        target_parent_id = maps.gc_hash_to_id.get(parent_hash) if parent_hash else None
        target_source_id = maps.gc_hash_to_id.get(source_hash) if source_hash else None

        if not target_parent_id or not target_source_id:
            stats.skipped_fk += 1
            continue

        if (target_parent_id, target_source_id) in existing:
            stats.already_exists += 1
            continue

        if dry_run:
            stats.synced += 1
            continue

        target.execute(
            generated_content_source_association.insert().values(
                parent_content_id=target_parent_id,
                source_content_id=target_source_id,
                relationship_type=rel_type or "derived_from",
            )
        )
        stats.synced += 1

    if not dry_run:
        target.commit()
    return stats


# ---------------------------------------------------------------------------
# Phase 6: page-content versions (the publishing layer the /c /f /d routes read)
#
# Immutable, versioned rows keyed by (scope, created_at). created_at is
# preserved on copy so "latest version per scope" ordering and cross-DB
# dedup both stay stable. Content slots (-> generated_content) are nullable
# and resolved best-effort; an unresolved required slot skips the row.
# ---------------------------------------------------------------------------

def sync_document_page_content(source: Session, target: Session, maps: NaturalKeyMaps, dry_run: bool) -> SyncStats:
    stats = SyncStats(table="document_page_content")
    source_rows = source.query(DocumentPageContent).all()
    stats.total_source = len(source_rows)

    for row in source_rows:
        doc_hash = _source_doc_hash(source, row.document_id)
        if not doc_hash:
            stats.skipped_fk += 1
            continue
        key = (doc_hash, row.created_at)

        existing_id = maps.doc_page_key_to_id.get(key)
        if existing_id:
            maps.src_page_id_to_target[row.id] = existing_id
            stats.already_exists += 1
            continue

        target_doc_id = maps.doc_hash_to_id.get(doc_hash)
        if not target_doc_id:
            stats.skipped_fk += 1
            continue

        if dry_run:
            stats.synced += 1
            continue

        new_id = uuid7()
        target.add(DocumentPageContent(
            id=new_id,
            document_id=target_doc_id,
            summary_content_id=_resolve_gc(source, maps, row.summary_content_id),
            intro_content_id=_resolve_gc(source, maps, row.intro_content_id),
            created_at=row.created_at,
        ))
        maps.src_page_id_to_target[row.id] = new_id
        maps.doc_page_key_to_id[key] = new_id
        stats.synced += 1

    if not dry_run:
        target.commit()
    return stats


def sync_filing_page_content(source: Session, target: Session, maps: NaturalKeyMaps, dry_run: bool) -> SyncStats:
    stats = SyncStats(table="filing_page_content")
    source_rows = source.query(FilingPageContent).all()
    stats.total_source = len(source_rows)

    for row in source_rows:
        accession = _source_filing_accession(source, row.filing_id)
        if not accession:
            stats.skipped_fk += 1
            continue
        key = (accession, row.created_at)

        existing_id = maps.filing_page_key_to_id.get(key)
        if existing_id:
            maps.src_page_id_to_target[row.id] = existing_id
            stats.already_exists += 1
            continue

        target_filing_id = maps.accession_to_filing_id.get(accession)
        if not target_filing_id:
            stats.skipped_fk += 1
            continue

        if dry_run:
            stats.synced += 1
            continue

        new_id = uuid7()
        target.add(FilingPageContent(
            id=new_id,
            filing_id=target_filing_id,
            main_content_id=_resolve_gc(source, maps, row.main_content_id),
            intro_content_id=_resolve_gc(source, maps, row.intro_content_id),
            created_at=row.created_at,
        ))
        maps.src_page_id_to_target[row.id] = new_id
        maps.filing_page_key_to_id[key] = new_id
        stats.synced += 1

    if not dry_run:
        target.commit()
    return stats


def sync_company_page_content(source: Session, target: Session, maps: NaturalKeyMaps, dry_run: bool) -> SyncStats:
    stats = SyncStats(table="company_page_content")
    source_rows = source.query(CompanyPageContent).all()
    stats.total_source = len(source_rows)

    for row in source_rows:
        ticker = _source_company_ticker(source, row.company_id)
        if not ticker:
            stats.skipped_fk += 1
            continue
        key = (ticker, row.created_at)

        existing_id = maps.company_page_key_to_id.get(key)
        if existing_id:
            maps.src_page_id_to_target[row.id] = existing_id
            stats.already_exists += 1
            continue

        target_company_id = maps.ticker_to_company_id.get(ticker)
        if not target_company_id:
            stats.skipped_fk += 1
            continue

        if dry_run:
            stats.synced += 1
            continue

        new_id = uuid7()
        target.add(CompanyPageContent(
            id=new_id,
            company_id=target_company_id,
            main_content_id=_resolve_gc(source, maps, row.main_content_id),
            intro_content_id=_resolve_gc(source, maps, row.intro_content_id),
            created_at=row.created_at,
        ))
        maps.src_page_id_to_target[row.id] = new_id
        maps.company_page_key_to_id[key] = new_id
        stats.synced += 1

    if not dry_run:
        target.commit()
    return stats


def sync_group_page_content(source: Session, target: Session, maps: NaturalKeyMaps, dry_run: bool) -> SyncStats:
    stats = SyncStats(table="group_page_content")
    source_rows = source.query(GroupPageContent).all()
    stats.total_source = len(source_rows)

    for row in source_rows:
        slug = _source_group_slug(source, row.company_group_id)
        if not slug:
            stats.skipped_fk += 1
            continue
        key = (slug, row.created_at)

        existing_id = maps.group_page_key_to_id.get(key)
        if existing_id:
            maps.src_page_id_to_target[row.id] = existing_id
            stats.already_exists += 1
            continue

        target_group_id = maps.slug_to_group_id.get(slug)
        if not target_group_id:
            stats.skipped_fk += 1
            continue

        if dry_run:
            stats.synced += 1
            continue

        new_id = uuid7()
        target.add(GroupPageContent(
            id=new_id,
            company_group_id=target_group_id,
            main_content_id=_resolve_gc(source, maps, row.main_content_id),
            intro_content_id=_resolve_gc(source, maps, row.intro_content_id),
            created_at=row.created_at,
        ))
        maps.src_page_id_to_target[row.id] = new_id
        maps.group_page_key_to_id[key] = new_id
        stats.synced += 1

    if not dry_run:
        target.commit()
    return stats


# ---------------------------------------------------------------------------
# Phase 7: page-content provenance (M2M) + change reports
#
# Parents are resolved via src_page_id_to_target (populated in Phase 6).
# Runs without an intervening build_maps() so that map survives.
# ---------------------------------------------------------------------------

def sync_filing_page_documents(source: Session, target: Session, maps: NaturalKeyMaps, dry_run: bool) -> SyncStats:
    stats = SyncStats(table="filing_page_content_document")
    source_assocs = source.execute(select(
        filing_page_content_document.c.filing_page_content_id,
        filing_page_content_document.c.document_id,
    )).all()
    stats.total_source = len(source_assocs)

    existing = set(target.execute(select(
        filing_page_content_document.c.filing_page_content_id,
        filing_page_content_document.c.document_id,
    )).all())

    for src_page_id, src_doc_id in source_assocs:
        target_page_id = maps.src_page_id_to_target.get(src_page_id)
        doc_hash = _source_doc_hash(source, src_doc_id)
        target_doc_id = maps.doc_hash_to_id.get(doc_hash) if doc_hash else None
        if not target_page_id or not target_doc_id:
            stats.skipped_fk += 1
            continue
        if (target_page_id, target_doc_id) in existing:
            stats.already_exists += 1
            continue
        if dry_run:
            stats.synced += 1
            continue
        target.execute(filing_page_content_document.insert().values(
            filing_page_content_id=target_page_id,
            document_id=target_doc_id,
        ))
        stats.synced += 1

    if not dry_run:
        target.commit()
    return stats


def sync_company_page_filings(source: Session, target: Session, maps: NaturalKeyMaps, dry_run: bool) -> SyncStats:
    stats = SyncStats(table="company_page_content_filing")
    source_assocs = source.execute(select(
        company_page_content_filing.c.company_page_content_id,
        company_page_content_filing.c.filing_id,
    )).all()
    stats.total_source = len(source_assocs)

    existing = set(target.execute(select(
        company_page_content_filing.c.company_page_content_id,
        company_page_content_filing.c.filing_id,
    )).all())

    for src_page_id, src_filing_id in source_assocs:
        target_page_id = maps.src_page_id_to_target.get(src_page_id)
        accession = _source_filing_accession(source, src_filing_id)
        target_filing_id = maps.accession_to_filing_id.get(accession) if accession else None
        if not target_page_id or not target_filing_id:
            stats.skipped_fk += 1
            continue
        if (target_page_id, target_filing_id) in existing:
            stats.already_exists += 1
            continue
        if dry_run:
            stats.synced += 1
            continue
        target.execute(company_page_content_filing.insert().values(
            company_page_content_id=target_page_id,
            filing_id=target_filing_id,
        ))
        stats.synced += 1

    if not dry_run:
        target.commit()
    return stats


def sync_group_page_companies(source: Session, target: Session, maps: NaturalKeyMaps, dry_run: bool) -> SyncStats:
    stats = SyncStats(table="group_page_content_company")
    source_assocs = source.execute(select(
        group_page_content_company.c.group_page_content_id,
        group_page_content_company.c.company_id,
    )).all()
    stats.total_source = len(source_assocs)

    existing = set(target.execute(select(
        group_page_content_company.c.group_page_content_id,
        group_page_content_company.c.company_id,
    )).all())

    for src_page_id, src_company_id in source_assocs:
        target_page_id = maps.src_page_id_to_target.get(src_page_id)
        ticker = _source_company_ticker(source, src_company_id)
        target_company_id = maps.ticker_to_company_id.get(ticker) if ticker else None
        if not target_page_id or not target_company_id:
            stats.skipped_fk += 1
            continue
        if (target_page_id, target_company_id) in existing:
            stats.already_exists += 1
            continue
        if dry_run:
            stats.synced += 1
            continue
        target.execute(group_page_content_company.insert().values(
            group_page_content_id=target_page_id,
            company_id=target_company_id,
        ))
        stats.synced += 1

    if not dry_run:
        target.commit()
    return stats


def sync_company_page_change_reports(source: Session, target: Session, maps: NaturalKeyMaps, dry_run: bool) -> SyncStats:
    stats = SyncStats(table="company_page_content_change_report")
    source_rows = source.execute(select(
        CompanyPageContentChangeReport.company_page_content_id,
        CompanyPageContentChangeReport.document_type,
        CompanyPageContentChangeReport.change_report_id,
        CompanyPageContentChangeReport.change_report_intro_id,
    )).all()
    stats.total_source = len(source_rows)

    existing = set(target.execute(select(
        CompanyPageContentChangeReport.company_page_content_id,
        CompanyPageContentChangeReport.document_type,
    )).all())

    for src_page_id, doc_type, src_cr_id, src_cr_intro_id in source_rows:
        target_page_id = maps.src_page_id_to_target.get(src_page_id)
        # change_report_id is NOT NULL — skip the row if it can't be resolved.
        target_cr_id = _resolve_gc(source, maps, src_cr_id)
        if not target_page_id or not target_cr_id:
            stats.skipped_fk += 1
            continue
        if (target_page_id, doc_type) in existing:
            stats.already_exists += 1
            continue
        if dry_run:
            stats.synced += 1
            continue
        target.add(CompanyPageContentChangeReport(
            company_page_content_id=target_page_id,
            document_type=doc_type,
            change_report_id=target_cr_id,
            change_report_intro_id=_resolve_gc(source, maps, src_cr_intro_id),
        ))
        stats.synced += 1

    if not dry_run:
        target.commit()
    return stats


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def print_summary(all_stats: List[SyncStats], dry_run: bool):
    """Print a Rich summary table of sync results."""
    table = Table(title="Sync Summary" + (" (DRY RUN)" if dry_run else ""))
    table.add_column("Table", style="cyan")
    table.add_column("Source", justify="right")
    table.add_column("Exists", justify="right", style="dim")
    table.add_column("Synced", justify="right", style="green")
    table.add_column("Skipped FK", justify="right", style="yellow")
    table.add_column("Errors", justify="right", style="red")

    for s in all_stats:
        table.add_row(
            s.table,
            str(s.total_source),
            str(s.already_exists),
            str(s.synced),
            str(s.skipped_fk),
            str(s.errors),
        )

    console.print(table)


def run_sync(source_url: str, target_url: str, dry_run: bool, batch_size: int = 500) -> List[SyncStats]:
    """Run the full sync from source to target database."""
    all_stats: List[SyncStats] = []

    console.print("[bold blue]Connecting to source...[/bold blue]")
    source = create_session(source_url)
    console.print("[bold blue]Connecting to target...[/bold blue]")
    target = create_session(target_url)

    # Verify connectivity
    try:
        source.execute(text("SELECT 1"))
        console.print("[green]Source connected[/green]")
    except Exception as e:
        console.print(f"[red]Cannot connect to source: {e}[/red]")
        sys.exit(1)

    try:
        target.execute(text("SELECT 1"))
        console.print("[green]Target connected[/green]")
    except Exception as e:
        console.print(f"[red]Cannot connect to target: {e}[/red]")
        sys.exit(1)

    if dry_run:
        console.print("[yellow]DRY RUN — no changes will be made[/yellow]")

    # Phase 1: no FK dependencies
    console.print("\n[bold]Phase 1: Base entities[/bold]")
    all_stats.append(sync_companies(source, target, dry_run))
    console.print(f"  companies: {all_stats[-1].synced} new")
    all_stats.append(sync_company_groups(source, target, dry_run))
    console.print(f"  company_groups: {all_stats[-1].synced} new")
    all_stats.append(sync_financial_concepts(source, target, dry_run))
    console.print(f"  financial_concepts: {all_stats[-1].synced} new")
    all_stats.append(sync_prompts(source, target, dry_run))
    console.print(f"  prompts: {all_stats[-1].synced} new")
    all_stats.append(sync_model_configs(source, target, dry_run))
    console.print(f"  model_configs: {all_stats[-1].synced} new")

    # Rebuild maps after phase 1
    maps = build_maps(target)

    # Phase 2: FK → Phase 1
    console.print("\n[bold]Phase 2: Filings & memberships[/bold]")
    all_stats.append(sync_filings(source, target, maps, dry_run))
    console.print(f"  filings: {all_stats[-1].synced} new, {all_stats[-1].skipped_fk} skipped")
    all_stats.append(sync_group_membership(source, target, maps, dry_run))
    console.print(f"  group_membership: {all_stats[-1].synced} new")

    # Rebuild maps after phase 2
    maps = build_maps(target)

    # Phase 3: FK → Phase 1+2
    console.print("\n[bold]Phase 3: Documents[/bold]")
    all_stats.append(sync_documents(source, target, maps, dry_run))
    console.print(f"  documents: {all_stats[-1].synced} new, {all_stats[-1].skipped_fk} skipped")

    # Rebuild maps after phase 3
    maps = build_maps(target)

    # Phase 4: FK → Phase 1-3
    console.print("\n[bold]Phase 4: Financial values & generated content[/bold]")
    all_stats.append(sync_financial_values(source, target, maps, dry_run))
    console.print(f"  financial_values: {all_stats[-1].synced} new, {all_stats[-1].skipped_fk} skipped")
    all_stats.append(sync_generated_content(source, target, maps, dry_run))
    console.print(f"  generated_content: {all_stats[-1].synced} new, {all_stats[-1].skipped_fk} skipped")

    # Rebuild maps after phase 4 (gc_hash_to_id updated in sync_generated_content)
    maps = build_maps(target)

    # Phase 5: association tables
    console.print("\n[bold]Phase 5: Associations[/bold]")
    all_stats.append(sync_gc_document_associations(source, target, maps, dry_run))
    console.print(f"  gc_document_assoc: {all_stats[-1].synced} new, {all_stats[-1].skipped_fk} skipped")
    all_stats.append(sync_gc_source_associations(source, target, maps, dry_run))
    console.print(f"  gc_source_assoc: {all_stats[-1].synced} new, {all_stats[-1].skipped_fk} skipped")

    # Phase 6: page-content versions (publishing layer behind /c /f /d routes).
    # Reuses the post-Phase-4 maps (Phase 5 added only association rows). Phase 6
    # populates maps.src_page_id_to_target, which Phase 7 consumes — so do NOT
    # rebuild maps between them (build_maps() returns a fresh, empty object).
    console.print("\n[bold]Phase 6: Page content[/bold]")
    all_stats.append(sync_document_page_content(source, target, maps, dry_run))
    console.print(f"  document_page_content: {all_stats[-1].synced} new, {all_stats[-1].skipped_fk} skipped")
    all_stats.append(sync_filing_page_content(source, target, maps, dry_run))
    console.print(f"  filing_page_content: {all_stats[-1].synced} new, {all_stats[-1].skipped_fk} skipped")
    all_stats.append(sync_company_page_content(source, target, maps, dry_run))
    console.print(f"  company_page_content: {all_stats[-1].synced} new, {all_stats[-1].skipped_fk} skipped")
    all_stats.append(sync_group_page_content(source, target, maps, dry_run))
    console.print(f"  group_page_content: {all_stats[-1].synced} new, {all_stats[-1].skipped_fk} skipped")

    # Phase 7: page-content provenance (M2M) + change reports
    console.print("\n[bold]Phase 7: Page content provenance[/bold]")
    all_stats.append(sync_filing_page_documents(source, target, maps, dry_run))
    console.print(f"  filing_page_content_document: {all_stats[-1].synced} new, {all_stats[-1].skipped_fk} skipped")
    all_stats.append(sync_company_page_filings(source, target, maps, dry_run))
    console.print(f"  company_page_content_filing: {all_stats[-1].synced} new, {all_stats[-1].skipped_fk} skipped")
    all_stats.append(sync_group_page_companies(source, target, maps, dry_run))
    console.print(f"  group_page_content_company: {all_stats[-1].synced} new, {all_stats[-1].skipped_fk} skipped")
    all_stats.append(sync_company_page_change_reports(source, target, maps, dry_run))
    console.print(f"  company_page_content_change_report: {all_stats[-1].synced} new, {all_stats[-1].skipped_fk} skipped")

    # Summary
    console.print()
    print_summary(all_stats, dry_run)

    # Cleanup
    source.close()
    target.close()

    return all_stats
