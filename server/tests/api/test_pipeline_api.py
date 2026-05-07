"""Tests for the pipeline API endpoints."""
from datetime import datetime
from unittest.mock import patch

from fastapi.testclient import TestClient
from symbology.api.main import create_app
from symbology.database.companies import Company
from symbology.database.jobs import Job, JobStatus, JobType
from symbology.database.pipeline_runs import PipelineRun, PipelineRunStatus, PipelineTrigger
from uuid_extensions import uuid7

client = TestClient(create_app())

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


class TestPipelineRunsApi:
    """Test class for pipeline run listing endpoints."""

    @patch("symbology.api.routes.pipeline.list_pipeline_runs")
    def test_list_runs(self, mock_list):
        mock_list.return_value = [SAMPLE_RUN]
        response = client.get("/pipeline/runs")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == str(SAMPLE_RUN_ID)
        assert data[0]["status"] == "completed"

    @patch("symbology.api.routes.pipeline.list_pipeline_runs")
    def test_list_runs_with_status_filter(self, mock_list):
        mock_list.return_value = []
        response = client.get("/pipeline/runs?status=completed")
        assert response.status_code == 200
        mock_list.assert_called_once_with(
            company_id=None,
            status=PipelineRunStatus.COMPLETED,
            limit=50,
            offset=0,
        )

    def test_list_runs_invalid_status(self):
        response = client.get("/pipeline/runs?status=bogus")
        assert response.status_code == 400
        assert "Invalid status" in response.json()["detail"]

    @patch("symbology.api.routes.pipeline.get_pipeline_run")
    def test_get_run_found(self, mock_get):
        mock_get.return_value = SAMPLE_RUN
        response = client.get(f"/pipeline/runs/{SAMPLE_RUN_ID}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(SAMPLE_RUN_ID)
        assert data["trigger"] == "manual"

    @patch("symbology.api.routes.pipeline.get_pipeline_run")
    def test_get_run_not_found(self, mock_get):
        mock_get.return_value = None
        response = client.get(f"/pipeline/runs/{SAMPLE_RUN_ID}")
        assert response.status_code == 404


class TestPipelineStatusApi:
    """Test class for the pipeline status dashboard endpoint."""

    @patch("symbology.api.routes.pipeline.get_company")
    @patch("symbology.api.routes.pipeline.count_consecutive_failures")
    @patch("symbology.api.routes.pipeline.get_latest_run_per_company")
    def test_status_dashboard(self, mock_latest, mock_failures, mock_company):
        mock_latest.return_value = [SAMPLE_RUN]
        mock_failures.return_value = 0
        mock_company.return_value = SAMPLE_COMPANY

        response = client.get("/pipeline/status")
        assert response.status_code == 200
        data = response.json()
        assert data["total_companies"] == 1
        assert data["companies_with_failures"] == 0
        assert data["stale_runs"] == 0
        assert len(data["companies"]) == 1
        assert data["companies"][0]["ticker"] == "ACME"

    @patch("symbology.api.routes.pipeline.get_company")
    @patch("symbology.api.routes.pipeline.count_consecutive_failures")
    @patch("symbology.api.routes.pipeline.get_latest_run_per_company")
    def test_status_dashboard_with_failures(self, mock_latest, mock_failures, mock_company):
        mock_latest.return_value = [SAMPLE_RUN]
        mock_failures.return_value = 3
        mock_company.return_value = SAMPLE_COMPANY

        response = client.get("/pipeline/status")
        assert response.status_code == 200
        data = response.json()
        assert data["companies_with_failures"] == 1
        assert data["companies"][0]["consecutive_failures"] == 3

    @patch("symbology.api.routes.pipeline.get_latest_run_per_company")
    def test_status_dashboard_empty(self, mock_latest):
        mock_latest.return_value = []
        response = client.get("/pipeline/status")
        assert response.status_code == 200
        data = response.json()
        assert data["total_companies"] == 0


class TestPipelineTriggerApi:
    """Test class for the pipeline trigger endpoint."""

    @patch("symbology.api.routes.pipeline.create_job")
    @patch("symbology.api.routes.pipeline.get_company_by_ticker")
    def test_trigger_pipeline(self, mock_get_company, mock_create_job):
        mock_get_company.return_value = SAMPLE_COMPANY
        mock_create_job.return_value = SAMPLE_JOB

        response = client.post("/pipeline/trigger/ACME")
        assert response.status_code == 201
        data = response.json()
        assert data["ticker"] == "ACME"
        assert data["job_id"] == str(SAMPLE_JOB_ID)

    @patch("symbology.api.routes.pipeline.get_company_by_ticker")
    def test_trigger_pipeline_not_found(self, mock_get_company):
        mock_get_company.return_value = None
        response = client.post("/pipeline/trigger/FAKE")
        assert response.status_code == 404
        assert "Company not found" in response.json()["detail"]

    @patch("symbology.api.routes.pipeline.create_job")
    @patch("symbology.api.routes.pipeline.get_company_by_ticker")
    def test_trigger_pipeline_with_forms(self, mock_get_company, mock_create_job):
        mock_get_company.return_value = SAMPLE_COMPANY
        mock_create_job.return_value = SAMPLE_JOB

        response = client.post(
            "/pipeline/trigger/ACME",
            json={"forms": ["10-K"]},
        )
        assert response.status_code == 201
        # Verify create_job was called with the custom forms
        call_kwargs = mock_create_job.call_args
        assert call_kwargs.kwargs["params"]["forms"] == ["10-K"]
