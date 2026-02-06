"""Tests for the pipeline CLI commands."""
from datetime import datetime
from unittest.mock import patch

from click.testing import CliRunner
from symbology.cli.pipeline import pipeline
from symbology.database.companies import Company
from symbology.database.jobs import Job, JobStatus, JobType
from symbology.database.pipeline_runs import PipelineRun, PipelineRunStatus, PipelineTrigger
from uuid_extensions import uuid7

runner = CliRunner()

SAMPLE_COMPANY_ID = uuid7()
SAMPLE_RUN_ID = uuid7()
SAMPLE_JOB_ID = uuid7()

SAMPLE_COMPANY = Company(
    id=SAMPLE_COMPANY_ID,
    name="Acme Corp",
    ticker="ACME",
    exchanges=["NYSE"],
)

SAMPLE_RUN = PipelineRun(
    id=SAMPLE_RUN_ID,
    company_id=SAMPLE_COMPANY_ID,
    trigger=PipelineTrigger.MANUAL,
    status=PipelineRunStatus.COMPLETED,
    forms=["10-K"],
    started_at=datetime(2025, 1, 1, 12, 0, 0),
    completed_at=datetime(2025, 1, 1, 12, 5, 0),
    jobs_created=3,
    jobs_completed=3,
    jobs_failed=0,
    run_metadata={},
)

SAMPLE_JOB = Job(
    id=SAMPLE_JOB_ID,
    job_type=JobType.FULL_PIPELINE,
    params={"ticker": "ACME", "forms": ["10-K", "10-Q"]},
    priority=1,
    status=JobStatus.PENDING,
    retry_count=0,
    max_retries=3,
)


class TestPipelineStatusCli:

    @patch("symbology.cli.pipeline.get_company")
    @patch("symbology.cli.pipeline.count_consecutive_failures")
    @patch("symbology.cli.pipeline.get_latest_run_per_company")
    @patch("symbology.cli.pipeline.init_session")
    def test_status_shows_table(self, mock_init, mock_latest, mock_failures, mock_company):
        mock_latest.return_value = [SAMPLE_RUN]
        mock_failures.return_value = 0
        mock_company.return_value = SAMPLE_COMPANY

        result = runner.invoke(pipeline, ["status"])
        assert result.exit_code == 0
        assert "ACME" in result.output
        assert "completed" in result.output

    @patch("symbology.cli.pipeline.get_latest_run_per_company")
    @patch("symbology.cli.pipeline.init_session")
    def test_status_empty(self, mock_init, mock_latest):
        mock_latest.return_value = []

        result = runner.invoke(pipeline, ["status"])
        assert result.exit_code == 0
        assert "No pipeline runs found" in result.output


class TestPipelineTriggerCli:

    @patch("symbology.cli.pipeline.create_job")
    @patch("symbology.cli.pipeline.get_company_by_ticker")
    @patch("symbology.cli.pipeline.init_session")
    def test_trigger_success(self, mock_init, mock_get_company, mock_create_job):
        mock_get_company.return_value = SAMPLE_COMPANY
        mock_create_job.return_value = SAMPLE_JOB

        result = runner.invoke(pipeline, ["trigger", "ACME"])
        assert result.exit_code == 0
        assert "Pipeline triggered" in result.output
        assert "ACME" in result.output

    @patch("symbology.cli.pipeline.get_company_by_ticker")
    @patch("symbology.cli.pipeline.init_session")
    def test_trigger_company_not_found(self, mock_init, mock_get_company):
        mock_get_company.return_value = None

        result = runner.invoke(pipeline, ["trigger", "FAKE"])
        assert result.exit_code == 1
        assert "Company not found" in result.output


class TestPipelineRunsCli:

    @patch("symbology.cli.pipeline.get_company")
    @patch("symbology.cli.pipeline.list_pipeline_runs")
    @patch("symbology.cli.pipeline.init_session")
    def test_runs_shows_table(self, mock_init, mock_list, mock_company):
        mock_list.return_value = [SAMPLE_RUN]
        mock_company.return_value = SAMPLE_COMPANY

        result = runner.invoke(pipeline, ["runs"])
        assert result.exit_code == 0
        assert "ACME" in result.output
        assert "completed" in result.output

    @patch("symbology.cli.pipeline.list_pipeline_runs")
    @patch("symbology.cli.pipeline.init_session")
    def test_runs_empty(self, mock_init, mock_list):
        mock_list.return_value = []

        result = runner.invoke(pipeline, ["runs"])
        assert result.exit_code == 0
        assert "No pipeline runs found" in result.output

    @patch("symbology.cli.pipeline.get_company_by_ticker")
    @patch("symbology.cli.pipeline.get_company")
    @patch("symbology.cli.pipeline.list_pipeline_runs")
    @patch("symbology.cli.pipeline.init_session")
    def test_runs_with_ticker_filter(self, mock_init, mock_list, mock_company, mock_get_by_ticker):
        mock_get_by_ticker.return_value = SAMPLE_COMPANY
        mock_list.return_value = [SAMPLE_RUN]
        mock_company.return_value = SAMPLE_COMPANY

        result = runner.invoke(pipeline, ["runs", "--ticker", "ACME"])
        assert result.exit_code == 0
        mock_list.assert_called_once_with(
            company_id=SAMPLE_COMPANY_ID,
            status=None,
            limit=20,
        )
