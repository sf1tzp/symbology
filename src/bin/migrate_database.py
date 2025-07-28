#!/usr/bin/env python3
"""
Database Migration Tool for Symbology

This script migrates data from a source database (typically development)
to a target database (typically staging or production).

Usage:
    python -m src.bin.migrate_database --help
    python -m src.bin.migrate_database --source dev --target staging
    python -m src.bin.migrate_database --dry-run
"""

import argparse
import sys
import time
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import tempfile
import subprocess
import os
from pathlib import Path

import psycopg2
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

from src.utils.config import settings
from src.utils.logging import configure_logging, get_logger

# Configure logging
configure_logging()
logger = get_logger(__name__)

class DatabaseMigrator:
    """Handles database migration between environments."""

    def __init__(self, source_url: str, target_url: str, dry_run: bool = False, auto_confirm: bool = False):
        self.source_url = source_url
        self.target_url = target_url
        self.dry_run = dry_run
        self.auto_confirm = auto_confirm

        # Parse database URLs to get connection details
        self.source_config = self._parse_db_url(source_url)
        self.target_config = self._parse_db_url(target_url)

        logger.info("database_migrator_initialized",
                   source=self.source_config['host'],
                   target=self.target_config['host'],
                   dry_run=dry_run,
                   auto_confirm=auto_confirm)

    def _parse_db_url(self, url: str) -> Dict[str, str]:
        """Parse PostgreSQL URL into components."""
        # postgresql://user:password@host:port/database
        from urllib.parse import urlparse
        parsed = urlparse(url)

        return {
            'host': parsed.hostname,
            'port': parsed.port or 5432,
            'username': parsed.username,
            'password': parsed.password,
            'database': parsed.path.lstrip('/')
        }

    def check_connectivity(self) -> Tuple[bool, bool]:
        """Check connectivity to both source and target databases with retry logic."""
        logger.info("checking_database_connectivity")

        source_ok = self._test_connection_with_retry(self.source_url, "source")
        target_ok = self._test_connection_with_retry(self.target_url, "target")

        return source_ok, target_ok

    def _test_connection_with_retry(self, url: str, name: str, max_retries: int = 5) -> bool:
        """Test connection to a database with retry logic for startup delays."""
        import time

        for attempt in range(max_retries):
            try:
                engine = create_engine(url)
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                logger.info(f"{name}_database_connection_successful", attempt=attempt + 1)
                return True
            except Exception as e:
                error_msg = str(e)

                # Check if it's a startup-related error
                is_startup_error = any(phrase in error_msg.lower() for phrase in [
                    "not yet accepting connections",
                    "consistent recovery state has not been yet reached",
                    "the database system is starting up",
                    "connection refused"
                ])

                if is_startup_error and attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff: 1, 2, 4, 8, 16 seconds
                    logger.warning(f"{name}_database_not_ready_retrying",
                                attempt=attempt + 1,
                                max_retries=max_retries,
                                wait_time=wait_time,
                                error=error_msg)
                    print(f"⏳ {name.title()} database not ready, waiting {wait_time}s before retry {attempt + 1}/{max_retries}...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"{name}_database_connection_failed",
                            attempt=attempt + 1,
                            error=error_msg)
                    if attempt == max_retries - 1:
                        print(f"❌ Failed to connect to {name} database after {max_retries} attempts")
                    return False

        return False

    def _test_connection(self, url: str, name: str) -> bool:
        """Test connection to a database (legacy method, kept for compatibility)."""
        return self._test_connection_with_retry(url, name, max_retries=1)

    def get_table_counts(self, url: str) -> Dict[str, int]:
        """Get row counts for all tables in the database."""
        counts = {}

        try:
            engine = create_engine(url)
            inspector = inspect(engine)
            table_names = inspector.get_table_names()

            with engine.connect() as conn:
                for table in table_names:
                    try:
                        result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                        counts[table] = result.scalar()
                    except Exception as e:
                        logger.warning(f"failed_to_count_table", table=table, error=str(e))
                        counts[table] = -1

        except Exception as e:
            logger.error("failed_to_get_table_counts", error=str(e))

        return counts

    def display_migration_plan(self):
        """Display the migration plan and database status."""
        print("\n" + "="*70)
        print("📋 MIGRATION PLAN")
        print("="*70)

        print(f"📊 Source Database (Development)")
        print(f"   Host: {self.source_config['host']}:{self.source_config['port']}")
        print(f"   Database: {self.source_config['database']}")
        print(f"   User: {self.source_config['username']}")

        target_env_name = "Target Database"
        if self.target_config['host'] in ['10.0.0.21', '10.0.0.22']:
            target_env_name = "Target Database (Staging)"
        elif self.target_config['host'] == 'localhost':
            target_env_name = "Target Database (Development)"

        print(f"\n🎯 {target_env_name}")
        print(f"   Host: {self.target_config['host']}:{self.target_config['port']}")
        print(f"   Database: {self.target_config['database']}")
        print(f"   User: {self.target_config['username']}")

        # Get current counts
        print(f"\n📈 Current Data Counts")
        print("-" * 30)

        source_counts = self.get_table_counts(self.source_url)
        target_counts = self.get_table_counts(self.target_url)

        # Key tables to highlight
        key_tables = ['companies', 'filings', 'documents', 'aggregates', 'completions', 'prompts']

        print(f"{'Table':<15} {'Source':<10} {'Target':<10} {'Status'}")
        print("-" * 50)

        for table in key_tables:
            source_count = source_counts.get(table, 0)
            target_count = target_counts.get(table, 0)

            if source_count > 0 and target_count == 0:
                status = "📤 Will migrate"
            elif source_count > 0 and target_count > 0:
                status = "🔄 Will replace"
            elif source_count == 0:
                status = "⚪ No data"
            else:
                status = "❓ Unknown"

            print(f"{table:<15} {source_count:<10} {target_count:<10} {status}")

        if self.dry_run:
            print(f"\n🏃 DRY RUN MODE - No changes will be made")

        print("="*70)

    def create_database_dump(self) -> Optional[str]:
        """Create a database dump from the source database with proper table ordering."""
        if self.dry_run:
            logger.info("dry_run_skipping_dump_creation")
            return "/tmp/fake_dump.sql"

        logger.info("creating_database_dump")

        # Create temporary file for the dump
        temp_file = tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.sql',
            prefix='symbology_migration_',
            delete=False
        )
        dump_file = temp_file.name
        temp_file.close()

        try:
            # First, check which tables exist in the source database
            source_engine = create_engine(self.source_url)
            with source_engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                """))
                existing_source_tables = {row[0] for row in result.fetchall()}
                logger.info("existing_source_tables", tables=sorted(existing_source_tables))

            # Define tables in dependency order, excluding completions for special handling
            tables_in_order = [
                'companies',
                'prompts',
                'filings',
                'documents',
                'financial_values',
                'aggregates',
                'completion_document_association',
                'aggregate_completion_association'
            ]

            # Filter to only tables that exist in the source
            existing_tables_in_order = [table for table in tables_in_order if table in existing_source_tables]
            logger.info("tables_to_dump", tables=existing_tables_in_order)

            if not existing_tables_in_order:
                logger.warning("no_tables_to_dump")
                # Create an empty dump file
                with open(dump_file, 'w') as f:
                    f.write("-- No tables to dump\n")
                return dump_file

            # Build pg_dump command with specific table order, excluding completions
            cmd = [
                'pg_dump',
                '--host', str(self.source_config['host']),
                '--port', str(self.source_config['port']),
                '--username', self.source_config['username'],
                '--dbname', self.source_config['database'],
                '--data-only',  # Only data, not schema
                '--verbose',
                '--disable-triggers',  # Disable triggers during dump
                '--file', dump_file
            ]

            # Add tables in specific order - only those that exist
            for table in existing_tables_in_order:
                cmd.extend(['--table', table])

            # Set password via environment variable
            env = os.environ.copy()
            env['PGPASSWORD'] = self.source_config['password']

            logger.info("running_pg_dump_with_table_order",
                       tables=existing_tables_in_order,
                       command=' '.join(cmd[:-2]))  # Don't log file path

            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            # Log pg_dump output for debugging
            if result.stdout:
                logger.info("pg_dump_stdout", output=result.stdout[:1000])  # First 1000 chars
            if result.stderr:
                logger.info("pg_dump_stderr", output=result.stderr[:1000])  # First 1000 chars

            if result.returncode != 0:
                logger.error("pg_dump_failed",
                           stderr=result.stderr,
                           stdout=result.stdout,
                           returncode=result.returncode)
                return None

            # Check file size and content preview
            file_size = os.path.getsize(dump_file)
            logger.info("dump_created_successfully",
                       file=dump_file,
                       size_mb=round(file_size / 1024 / 1024, 2))

            # Preview dump file content to see what tables are included
            try:
                with open(dump_file, 'r') as f:
                    first_lines = []
                    copy_statements = []
                    for i, line in enumerate(f):
                        if i < 20:  # First 20 lines
                            first_lines.append(line.strip())
                        if 'COPY ' in line and ' FROM stdin;' in line:
                            copy_statements.append(line.strip())
                        if i > 1000:  # Don't read entire file
                            break

                    logger.info("dump_file_preview",
                               first_lines=first_lines[:10],
                               copy_statements=copy_statements)
            except Exception as e:
                logger.warning("could_not_preview_dump_file", error=str(e))

            return dump_file

        except subprocess.TimeoutExpired:
            logger.error("pg_dump_timeout")
            return None
        except Exception as e:
            logger.error("pg_dump_exception", error=str(e))
            return None

    def _prepare_target_database(self) -> bool:
        """Prepare target database by clearing data and disabling constraints."""
        try:
            logger.info("clearing_target_database_tables")

            # First, check which tables actually exist in the target database
            engine = create_engine(self.target_url)
            with engine.connect() as conn:
                # Get list of existing tables
                result = conn.execute(text("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                """))
                existing_tables = {row[0] for row in result.fetchall()}
                logger.info("existing_target_tables", tables=sorted(existing_tables))

            # Order matters! Delete in reverse dependency order to avoid FK violations
            tables_to_clear = [
                'completion_document_association',  # Association tables first
                'aggregate_completion_association',
                'completions',
                'documents',
                'filings',
                'financial_values',
                'aggregates',
                'companies',  # Clear companies too to avoid PK conflicts
                'prompts',    # Clear prompts too to avoid PK conflicts
            ]

            # Filter to only tables that actually exist
            tables_to_clear = [table for table in tables_to_clear if table in existing_tables]
            logger.info("tables_to_clear", tables=tables_to_clear)

            with engine.connect() as conn:
                # Start transaction
                trans = conn.begin()
                try:
                    # Disable foreign key constraints temporarily
                    logger.info("disabling_foreign_key_constraints")
                    conn.execute(text("SET session_replication_role = replica;"))

                    # Clear tables in dependency order - only tables that exist
                    for table in tables_to_clear:
                        try:
                            result = conn.execute(text(f"DELETE FROM {table}"))
                            logger.info("cleared_table", table=table, rows_deleted=result.rowcount)
                        except Exception as e:
                            # Even with existence check, handle any errors gracefully
                            logger.warning("could_not_clear_table", table=table, error=str(e))
                            # Don't let this fail the entire transaction - just continue
                            trans.rollback()
                            # Start a new transaction
                            trans = conn.begin()
                            # Re-disable constraints for the new transaction
                            conn.execute(text("SET session_replication_role = replica;"))

                    # Re-enable foreign key constraints
                    logger.info("re_enabling_foreign_key_constraints")
                    conn.execute(text("SET session_replication_role = DEFAULT;"))

                    trans.commit()
                    logger.info("target_database_prepared_successfully")
                    return True

                except Exception as e:
                    trans.rollback()
                    logger.error("failed_to_prepare_target_database", error=str(e))
                    return False

        except Exception as e:
            logger.error("prepare_target_database_exception", error=str(e))
            return False

    def _ensure_target_schema_exists(self) -> bool:
        """Ensure the target database has the required schema (tables)."""
        try:
            # Check if target database has any tables
            engine = create_engine(self.target_url)
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT COUNT(*)
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                """))
                table_count = result.scalar()

                if table_count > 0:
                    logger.info("target_database_has_schema", table_count=table_count)
                    return True

                logger.warning("target_database_missing_schema",
                             message="Target database has no tables. Creating schema from source.")

                # Create schema dump from source
                return self._create_and_apply_schema()

        except Exception as e:
            logger.error("schema_check_failed", error=str(e))
            return False

    def _create_and_apply_schema(self) -> bool:
        """Create and apply database schema from source to target."""
        try:
            logger.info("creating_schema_dump_from_source")

            # Create temporary file for schema dump
            temp_file = tempfile.NamedTemporaryFile(
                mode='w',
                suffix='_schema.sql',
                prefix='symbology_schema_',
                delete=False
            )
            schema_file = temp_file.name
            temp_file.close()

            # Create schema-only dump from source
            cmd = [
                'pg_dump',
                '--host', str(self.source_config['host']),
                '--port', str(self.source_config['port']),
                '--username', self.source_config['username'],
                '--dbname', self.source_config['database'],
                '--schema-only',  # Only schema, not data
                '--no-owner',     # Don't include ownership commands
                '--no-privileges', # Don't include privileges
                '--file', schema_file
            ]

            # Set password via environment variable
            env = os.environ.copy()
            env['PGPASSWORD'] = self.source_config['password']

            logger.info("running_schema_dump", command=' '.join(cmd[:-2]))

            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=120  # 2 minute timeout for schema
            )

            if result.returncode != 0:
                logger.error("schema_dump_failed",
                           stderr=result.stderr,
                           stdout=result.stdout)
                return False

            logger.info("schema_dump_created", file=schema_file)

            # Apply schema to target database
            return self._apply_schema_to_target(schema_file)

        except Exception as e:
            logger.error("schema_creation_failed", error=str(e))
            return False
        finally:
            # Clean up schema file
            if 'schema_file' in locals() and os.path.exists(schema_file):
                os.unlink(schema_file)
                logger.info("schema_file_cleaned_up")

    def _apply_schema_to_target(self, schema_file: str) -> bool:
        """Apply schema file to target database."""
        try:
            logger.info("applying_schema_to_target", file=schema_file)

            # Build psql command to apply schema
            cmd = [
                'psql',
                '--host', str(self.target_config['host']),
                '--port', str(self.target_config['port']),
                '--username', self.target_config['username'],
                '--dbname', self.target_config['database'],
                '--file', schema_file,
                '--quiet'
            ]

            # Set password via environment variable
            env = os.environ.copy()
            env['PGPASSWORD'] = self.target_config['password']

            logger.info("running_schema_restore", command=' '.join(cmd))

            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            if result.returncode != 0:
                logger.error("schema_restore_failed",
                           stderr=result.stderr,
                           stdout=result.stdout)
                return False

            logger.info("schema_applied_successfully")

            # Verify schema was created
            engine = create_engine(self.target_url)
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT COUNT(*)
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                """))
                table_count = result.scalar()
                logger.info("schema_verification", table_count=table_count)

                if table_count == 0:
                    logger.error("schema_verification_failed",
                               message="No tables found after schema application")
                    return False

            return True

        except Exception as e:
            logger.error("schema_application_failed", error=str(e))
            return False

    def _migrate_completions_data(self) -> bool:
        """Migrate completions data with schema compatibility."""
        if self.dry_run:
            logger.info("dry_run_skipping_completions_migration")
            return True

        try:
            logger.info("migrating_completions_data_with_schema_mapping")

            # First check if completions table exists in target
            target_engine = create_engine(self.target_url)
            with target_engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT COUNT(*)
                    FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_name = 'completions'
                """))
                if result.scalar() == 0:
                    logger.warning("completions_table_missing_in_target",
                                 message="Completions table doesn't exist in target, skipping completions migration")
                    return True

            # Get completions data from source with only compatible columns
            source_engine = create_engine(self.source_url)

            # Query source data with only the columns that exist in target
            query = """
                SELECT
                    id, system_prompt_id, model, temperature, top_p, content,
                    created_at, total_duration, num_ctx, top_k
                FROM completions
            """

            with source_engine.connect() as source_conn:
                with target_engine.connect() as target_conn:
                    # Disable constraints temporarily
                    target_conn.execute(text("SET session_replication_role = replica;"))

                    # Fetch data from source
                    result = source_conn.execute(text(query))
                    rows = result.fetchall()
                    columns = result.keys()

                    logger.info("fetched_completions_data", row_count=len(rows))

                    if rows:
                        # Build insert statement for target
                        column_names = ', '.join(columns)
                        placeholders = ', '.join([f':{col}' for col in columns])
                        insert_query = f"INSERT INTO completions ({column_names}) VALUES ({placeholders})"

                        # Insert data in batches
                        batch_size = 100
                        for i in range(0, len(rows), batch_size):
                            batch = rows[i:i + batch_size]
                            # Convert rows to dictionaries for SQLAlchemy
                            batch_dicts = [dict(zip(columns, row)) for row in batch]
                            target_conn.execute(text(insert_query), batch_dicts)
                            logger.info("inserted_completions_batch",
                                      batch_start=i,
                                      batch_size=len(batch_dicts))

                    # Re-enable constraints
                    target_conn.execute(text("SET session_replication_role = DEFAULT;"))
                    target_conn.commit()

                    logger.info("completions_migration_completed", total_rows=len(rows))
                    return True

        except Exception as e:
            logger.error("completions_migration_failed", error=str(e))
            return False

    def restore_database_dump(self, dump_file: str) -> bool:
        """Restore the database dump to the target database."""
        if self.dry_run:
            logger.info("dry_run_skipping_restore")
            return True

        logger.info("restoring_database_dump", file=dump_file)

        try:
            # First, check if target database has any tables (schema)
            logger.info("checking_target_database_schema")
            if not self._ensure_target_schema_exists():
                logger.error("failed_to_ensure_target_schema")
                return False

            # Then, disable foreign key constraints and clear existing data
            logger.info("preparing_target_database_for_restore")
            if not self._prepare_target_database():
                return False

            # Build psql command
            cmd = [
                'psql',
                '--host', str(self.target_config['host']),
                '--port', str(self.target_config['port']),
                '--username', self.target_config['username'],
                '--dbname', self.target_config['database'],
                '--file', dump_file,
                '--quiet'
            ]

            # Set password via environment variable
            env = os.environ.copy()
            env['PGPASSWORD'] = self.target_config['password']

            logger.info("running_psql_restore", command=" ".join(cmd))

            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )

            # Log both stdout and stderr for debugging
            if result.stdout:
                logger.info("psql_restore_stdout", stdout=result.stdout[:1000])  # First 1000 chars
            if result.stderr:
                logger.warning("psql_restore_stderr", stderr=result.stderr[:1000])  # First 1000 chars

            if result.returncode != 0:
                logger.error("psql_restore_failed",
                           stderr=result.stderr,
                           stdout=result.stdout,
                           returncode=result.returncode)
                return False

            # Re-enable foreign key constraints and triggers
            logger.info("re_enabling_constraints_after_restore")
            if not self._re_enable_constraints():
                logger.warning("failed_to_re_enable_constraints")

            logger.info("restore_completed_successfully", returncode=result.returncode)
            return True

        except subprocess.TimeoutExpired:
            logger.error("psql_restore_timeout")
            return False
        except Exception as e:
            logger.error("psql_restore_exception", error=str(e))
            return False

    def _re_enable_constraints(self) -> bool:
        """Re-enable foreign key constraints and triggers after restore."""
        try:
            engine = create_engine(self.target_url)
            with engine.connect() as conn:
                # Re-enable foreign key constraints and triggers
                conn.execute(text("SET session_replication_role = DEFAULT;"))
                conn.commit()
                logger.info("constraints_re_enabled_successfully")
                return True
        except Exception as e:
            logger.error("failed_to_re_enable_constraints", error=str(e))
            return False

    def _check_table_schemas(self):
        """Check table schemas and constraints in both databases."""
        try:
            logger.info("checking_database_schemas")

            # Check tables in source
            with psycopg2.connect(self.source_url) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT table_name
                        FROM information_schema.tables
                        WHERE table_schema = 'public'
                        ORDER BY table_name
                    """)
                    source_tables = [row[0] for row in cur.fetchall()]
                    logger.info("source_tables", tables=source_tables)

                    # Check foreign key constraints
                    cur.execute("""
                        SELECT
                            tc.table_name,
                            tc.constraint_name,
                            ccu.table_name AS foreign_table_name,
                            ccu.column_name AS foreign_column_name
                        FROM information_schema.table_constraints AS tc
                        JOIN information_schema.constraint_column_usage AS ccu
                        ON ccu.constraint_name = tc.constraint_name
                        WHERE tc.constraint_type = 'FOREIGN KEY'
                        ORDER BY tc.table_name
                    """)
                    source_fks = cur.fetchall()
                    logger.info("source_foreign_keys", count=len(source_fks),
                               constraints=[(fk[0], fk[1], f"{fk[2]}.{fk[3]}") for fk in source_fks])

            # Check tables in target
            with psycopg2.connect(self.target_url) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT table_name
                        FROM information_schema.tables
                        WHERE table_schema = 'public'
                        ORDER BY table_name
                    """)
                    target_tables = [row[0] for row in cur.fetchall()]
                    logger.info("target_tables", tables=target_tables)

        except Exception as e:
            logger.warning("schema_check_failed", error=str(e))

    def verify_migration(self) -> bool:
        """Verify that the migration was successful."""
        logger.info("verifying_migration")

        try:
            source_counts = self.get_table_counts(self.source_url)
            target_counts = self.get_table_counts(self.target_url)

            print(f"\n✅ MIGRATION VERIFICATION")
            print("-" * 40)

            # Key tables to verify
            key_tables = ['companies', 'filings', 'documents', 'aggregates', 'completions']

            all_good = True

            for table in key_tables:
                source_count = source_counts.get(table, 0)
                target_count = target_counts.get(table, 0)

                if source_count == target_count:
                    print(f"✅ {table}: {target_count} rows (matches source)")
                    logger.info("table_verification_passed", table=table, count=target_count)
                else:
                    print(f"❌ {table}: {target_count} rows (source has {source_count})")
                    logger.warning("table_verification_failed",
                                 table=table,
                                 target_count=target_count,
                                 source_count=source_count)
                    all_good = False

            if all_good:
                print(f"\n🎉 Migration verification PASSED")
                logger.info("migration_verification_passed")
            else:
                print(f"\n⚠️  Migration verification FAILED")
                logger.error("migration_verification_failed")

            return all_good

        except Exception as e:
            logger.error("migration_verification_exception", error=str(e))
            return False

    def run_migration(self) -> bool:
        """Run the complete migration process."""
        start_time = time.time()

        print(f"\n🚀 Starting Database Migration")
        print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # 1. Display migration plan
        self.display_migration_plan()

        # 2. Check connectivity
        source_ok, target_ok = self.check_connectivity()
        if not source_ok or not target_ok:
            logger.error("connectivity_check_failed")
            return False

        # 3. Confirm migration (unless dry run or auto-confirm)
        if not self.dry_run:
            print(f"\n⚠️  This will REPLACE all data in the target database!")
            if self.auto_confirm:
                print("🤖 Auto-confirm enabled, proceeding with migration...")
                logger.info("migration_auto_confirmed")
            else:
                confirm = input("Are you sure you want to continue? (yes/no): ")
                if confirm.lower() != 'yes':
                    print("Migration cancelled.")
                    return False

        # 4. Create dump
        dump_file = self.create_database_dump()
        if not dump_file:
            logger.error("dump_creation_failed")
            return False

        try:
            # 5. Restore dump (all tables except completions)
            if not self.restore_database_dump(dump_file):
                logger.error("restore_failed")
                return False

            # 6. Migrate completions separately to handle schema differences
            if not self._migrate_completions_data():
                logger.error("completions_migration_failed")
                return False

            # 7. Verify migration
            if not self.verify_migration():
                logger.error("verification_failed")
                return False

            duration = time.time() - start_time
            print(f"\n🎉 Migration completed successfully in {duration:.1f} seconds!")
            logger.info("migration_completed_successfully", duration=duration)

            return True

        finally:
            # Clean up dump file
            if not self.dry_run and dump_file and os.path.exists(dump_file):
                os.unlink(dump_file)
                logger.info("temporary_dump_file_cleaned_up")


def get_database_url(environment: str) -> str:
    """Get database URL for the specified environment."""
    base_url = settings.database.url

    if environment == 'dev':
        return base_url
    elif environment == 'staging':
        # Replace host with staging host
        return base_url.replace(settings.database.host, "10.0.0.21")
    elif environment.startswith('staging-') or environment.replace('.', '').replace('-', '').isdigit():
        # Handle specific staging hosts or IP addresses
        if '.' in environment:  # IP address
            target_host = environment
        else:  # staging-1g, staging-2g, etc. - use default staging IP
            target_host = "10.0.0.21"
        return base_url.replace(settings.database.host, target_host)
    else:
        raise ValueError(f"Unknown environment: {environment}")


def main():
    """Main entry point for the database migration tool."""
    parser = argparse.ArgumentParser(
        description="Migrate database data between environments",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Migrate from dev to staging
  python -m src.bin.migrate_database --source dev --target staging

  # Migrate to specific staging host
  python -m src.bin.migrate_database --source dev --target staging-1g

  # Migrate to specific IP address
  python -m src.bin.migrate_database --source dev --target 10.0.0.21

  # Migrate with auto-confirmation (for automation)
  python -m src.bin.migrate_database --source dev --target staging -y

  # Dry run to see what would happen
  python -m src.bin.migrate_database --source dev --target staging --dry-run

  # Check status of both databases
  python -m src.bin.migrate_database --status-only
        """
    )

    parser.add_argument(
        '--source',
        choices=['dev'],
        default='dev',
        help='Source environment (default: dev)'
    )

    parser.add_argument(
        '--target',
        default='staging',
        help='Target environment (default: staging). Can be "staging", specific staging host like "staging-1g", or IP address like "10.0.0.21"'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be migrated without making changes'
    )

    parser.add_argument(
        '--status-only',
        action='store_true',
        help='Only show current database status'
    )

    parser.add_argument(
        '-y', '--yes',
        action='store_true',
        help='Automatically confirm migration without prompting (useful for automation)'
    )

    args = parser.parse_args()

    try:
        # Get database URLs
        source_url = get_database_url(args.source)
        target_url = get_database_url(args.target)

        # Create migrator
        migrator = DatabaseMigrator(source_url, target_url, args.dry_run, auto_confirm=args.yes)

        if args.status_only:
            migrator.display_migration_plan()
            return

        # Run migration
        success = migrator.run_migration()

        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n\nMigration cancelled by user.")
        sys.exit(1)
    except Exception as e:
        logger.error("migration_script_exception", error=str(e))
        print(f"\n❌ Migration failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
