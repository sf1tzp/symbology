"""Tests for the jobs API endpoints."""
from unittest.mock import patch

from fastapi.testclient import TestClient
from symbology.api.main import create_app
from symbology.database.jobs import Job, JobStatus, JobType
from uuid_extensions import uuid7

client = TestClient(create_app())

SAMPLE_JOB_ID = uuid7()
SAMPLE_JOB = Job(
    id=SAMPLE_JOB_ID,
    job_type=JobType.TEST,
    params={"key": "value"},
    priority=2,
    status=JobStatus.PENDING,
    retry_count=0,
    max_retries=3,
)


class TestJobsApi:
    """Test class for Jobs API endpoints."""

    @patch("symbology.api.routes.jobs.create_job")
    def test_enqueue_job(self, mock_create):
        mock_create.return_value = SAMPLE_JOB
        response = client.post("/jobs/", json={
            "job_type": "test",
            "params": {"key": "value"},
            "priority": 2,
        })
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == str(SAMPLE_JOB_ID)
        assert data["job_type"] == "test"
        assert data["status"] == "pending"
        mock_create.assert_called_once()

    def test_enqueue_invalid_type(self):
        response = client.post("/jobs/", json={
            "job_type": "nonexistent_type",
            "params": {},
        })
        assert response.status_code == 400
        assert "Invalid job_type" in response.json()["detail"]

    @patch("symbology.api.routes.jobs.get_job")
    def test_get_job_found(self, mock_get):
        mock_get.return_value = SAMPLE_JOB
        response = client.get(f"/jobs/{SAMPLE_JOB_ID}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(SAMPLE_JOB_ID)
        mock_get.assert_called_once_with(SAMPLE_JOB_ID)

    @patch("symbology.api.routes.jobs.get_job")
    def test_get_job_not_found(self, mock_get):
        mock_get.return_value = None
        response = client.get(f"/jobs/{SAMPLE_JOB_ID}")
        assert response.status_code == 404

    @patch("symbology.api.routes.jobs.list_jobs")
    def test_list_jobs(self, mock_list):
        mock_list.return_value = [SAMPLE_JOB]
        response = client.get("/jobs/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["job_type"] == "test"

    @patch("symbology.api.routes.jobs.list_jobs")
    def test_list_jobs_with_status_filter(self, mock_list):
        mock_list.return_value = []
        response = client.get("/jobs/?status=pending")
        assert response.status_code == 200
        mock_list.assert_called_once_with(
            status=JobStatus.PENDING,
            job_type=None,
            limit=50,
            offset=0,
        )

    def test_list_jobs_invalid_status(self):
        response = client.get("/jobs/?status=bogus")
        assert response.status_code == 400
        assert "Invalid status" in response.json()["detail"]

    @patch("symbology.api.routes.jobs.cancel_job")
    def test_cancel_job(self, mock_cancel):
        cancelled = Job(
            id=SAMPLE_JOB_ID,
            job_type=JobType.TEST,
            params={},
            priority=2,
            status=JobStatus.CANCELLED,
            retry_count=0,
            max_retries=3,
        )
        mock_cancel.return_value = cancelled
        response = client.delete(f"/jobs/{SAMPLE_JOB_ID}")
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"

    @patch("symbology.api.routes.jobs.cancel_job")
    def test_cancel_job_not_found(self, mock_cancel):
        mock_cancel.return_value = None
        response = client.delete(f"/jobs/{SAMPLE_JOB_ID}")
        assert response.status_code == 404

    def test_get_job_invalid_uuid(self):
        response = client.get("/jobs/not-a-uuid")
        assert response.status_code == 422
