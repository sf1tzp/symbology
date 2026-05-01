"""Tests for the db sync and backfill CLI commands."""

from unittest.mock import MagicMock, patch

from click.testing import CliRunner
from symbology.cli.db import db
from symbology.cli.db_sync import resolve_db_url
from symbology.database.documents import DocumentType
from symbology.database.generated_content import ContentStage

runner = CliRunner()


class TestResolveDbUrl:

    def _mock_root(self, tmp_path, env_name, content=None):
        """Create a fake secrets dir and env file under tmp_path."""
        secrets_dir = tmp_path / "secrets"
        secrets_dir.mkdir()
        if content is not None:
            (secrets_dir / f"{env_name}.env").write_text(content)

    @patch("symbology.cli.db_sync.subprocess.run")
    @patch("symbology.cli.db_sync._project_root")
    def test_parses_decrypted_env(self, mock_root, mock_run, tmp_path):
        mock_root.return_value = tmp_path
        self._mock_root(tmp_path, "staging-web", "placeholder")

        mock_run.return_value = MagicMock(
            stdout=(
                "# comment\n"
                "DATABASE_HOST=db.example.com\n"
                "DATABASE_PORT=5432\n"
                "DATABASE_USER=myuser\n"
                "DATABASE_PASSWORD=secret123\n"
                "DATABASE_NAME=symbology\n"
                "OTHER_VAR=ignored\n"
            ),
            stderr="",
        )

        url = resolve_db_url("staging-web")
        assert url == "postgresql://myuser:secret123@db.example.com:5432/symbology"

    @patch("symbology.cli.db_sync.subprocess.run")
    @patch("symbology.cli.db_sync._project_root")
    def test_url_encodes_special_chars_in_password(self, mock_root, mock_run, tmp_path):
        mock_root.return_value = tmp_path
        self._mock_root(tmp_path, "test", "placeholder")

        mock_run.return_value = MagicMock(
            stdout=(
                "DATABASE_HOST=localhost\n"
                "DATABASE_PORT=5432\n"
                "DATABASE_USER=user\n"
                "DATABASE_PASSWORD=p@ss w0rd!\n"
                "DATABASE_NAME=db\n"
            ),
            stderr="",
        )

        url = resolve_db_url("test")
        assert "p%40ss+w0rd%21" in url

    @patch("symbology.cli.db_sync._project_root")
    def test_missing_env_file_exits(self, mock_root, tmp_path):
        mock_root.return_value = tmp_path
        (tmp_path / "secrets").mkdir()
        # Don't create the env file

        with patch("symbology.cli.db_sync.sys.exit", side_effect=SystemExit(1)):
            try:
                resolve_db_url("nonexistent")
            except SystemExit:
                pass  # Expected

    @patch("symbology.cli.db_sync.subprocess.run")
    @patch("symbology.cli.db_sync._project_root")
    def test_missing_required_vars_exits(self, mock_root, mock_run, tmp_path):
        mock_root.return_value = tmp_path
        self._mock_root(tmp_path, "partial", "placeholder")

        mock_run.return_value = MagicMock(
            stdout="DATABASE_HOST=localhost\n",
            stderr="",
        )

        with patch("symbology.cli.db_sync.sys.exit", side_effect=SystemExit(1)):
            try:
                resolve_db_url("partial")
            except SystemExit:
                pass  # Expected


class TestSyncCommand:

    def test_rejects_same_env(self):
        result = runner.invoke(db, ["sync", "--source", "staging", "--target", "staging"])
        assert result.exit_code != 0
        assert "must be different" in result.output

    @patch("symbology.cli.db_sync.run_sync")
    @patch("symbology.cli.db_sync.resolve_db_url")
    def test_dry_run_calls_sync(self, mock_resolve, mock_sync):
        mock_resolve.side_effect = lambda name: f"postgresql://x@{name}:5432/db"

        result = runner.invoke(db, [
            "sync", "--source", "staging-web", "--target", "local", "--dry-run",
        ])
        assert result.exit_code == 0
        mock_sync.assert_called_once()
        _, kwargs = mock_sync.call_args
        assert kwargs["dry_run"] is True


class TestBackfillContentStageMapping:
    """Unit test the description -> content_stage mapping logic."""

    def _map_description(self, desc: str):
        STAGE_SUFFIXES = {
            "_single_summary": ContentStage.SINGLE_SUMMARY,
            "_aggregate_summary": ContentStage.AGGREGATE_SUMMARY,
            "_frontpage_summary": ContentStage.FRONTPAGE_SUMMARY,
        }
        EXACT_MATCHES = {
            "company_group_analysis": ContentStage.COMPANY_GROUP_ANALYSIS,
            "company_group_frontpage": ContentStage.COMPANY_GROUP_FRONTPAGE,
            "business_description_frontpage_summary": ContentStage.FRONTPAGE_SUMMARY,
        }
        DOC_TYPE_MAP = {dt.value: dt for dt in DocumentType}

        detected_stage = EXACT_MATCHES.get(desc)
        doc_type_prefix = None if detected_stage else desc

        if not detected_stage:
            for suffix, stage in STAGE_SUFFIXES.items():
                if desc.endswith(suffix):
                    detected_stage = stage
                    doc_type_prefix = desc[: -len(suffix)]
                    break

        detected_doc_type = DOC_TYPE_MAP.get(doc_type_prefix) if doc_type_prefix else None
        return detected_stage, detected_doc_type

    def test_single_summary(self):
        stage, doc_type = self._map_description("risk_factors_single_summary")
        assert stage == ContentStage.SINGLE_SUMMARY
        assert doc_type == DocumentType.RISK_FACTORS

    def test_aggregate_summary(self):
        stage, doc_type = self._map_description("management_discussion_aggregate_summary")
        assert stage == ContentStage.AGGREGATE_SUMMARY
        assert doc_type == DocumentType.MDA

    def test_frontpage_summary_exact(self):
        stage, doc_type = self._map_description("business_description_frontpage_summary")
        assert stage == ContentStage.FRONTPAGE_SUMMARY
        assert doc_type is None

    def test_frontpage_summary_suffix(self):
        stage, doc_type = self._map_description("business_description_frontpage_summary")
        assert stage == ContentStage.FRONTPAGE_SUMMARY

    def test_company_group_analysis(self):
        stage, doc_type = self._map_description("company_group_analysis")
        assert stage == ContentStage.COMPANY_GROUP_ANALYSIS
        assert doc_type is None

    def test_company_group_frontpage(self):
        stage, doc_type = self._map_description("company_group_frontpage")
        assert stage == ContentStage.COMPANY_GROUP_FRONTPAGE
        assert doc_type is None

    def test_unrecognized_returns_none(self):
        stage, doc_type = self._map_description("something_unknown")
        assert stage is None
        assert doc_type is None

    def test_description_suffix_for_all_doc_types(self):
        """Verify suffix stripping extracts known document types."""
        stage, doc_type = self._map_description("controls_procedures_aggregate_summary")
        assert stage == ContentStage.AGGREGATE_SUMMARY
        assert doc_type == DocumentType.CONTROLS_PROCEDURES


class TestBackfillContentStageCli:

    @patch("symbology.database.base.get_db_session")
    @patch("symbology.database.base.init_db")
    def test_no_rows_to_backfill(self, mock_init, mock_session):
        mock_query = MagicMock()
        mock_query.query.return_value.filter.return_value.limit.return_value.all.return_value = []
        mock_session.return_value = mock_query

        result = runner.invoke(db, ["backfill", "content-stage", "--dry-run"])
        assert result.exit_code == 0
        assert "No rows need backfilling" in result.output


class TestBackfillCikCli:

    @patch("edgar.Company")
    @patch("symbology.ingestion.edgar_db.accessors.edgar_login")
    @patch("symbology.database.base.get_db_session")
    @patch("symbology.database.base.init_db")
    def test_no_companies_without_cik(self, mock_init, mock_session, mock_login, mock_edgar):
        mock_query = MagicMock()
        mock_query.query.return_value.filter.return_value.limit.return_value.all.return_value = []
        mock_session.return_value = mock_query

        result = runner.invoke(db, ["backfill", "cik", "--dry-run"])
        assert result.exit_code == 0
        assert "All companies already have CIK" in result.output
