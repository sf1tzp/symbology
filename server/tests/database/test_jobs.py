"""Tests for the jobs database module."""
from unittest.mock import patch
from datetime import datetime, timedelta, timezone

from uuid_extensions import uuid7
import pytest

from symbology.database.jobs import (
    Job,
    JobStatus,
    JobType,
    cancel_failed_jobs,
    cancel_job,
    claim_next_job,
    complete_job,
    count_jobs_by_status,
    create_job,
    fail_job,
    get_job,
    list_jobs,
    mark_stale_jobs_as_failed,
    requeue_failed_jobs,
)


pytestmark = pytest.mark.integration

class TestJobModel:
    """Test the Job ORM model."""

    def test_create_job_instance(self):
        job = Job(
            job_type=JobType.TEST,
            params={"key": "value"},
            priority=1,
            status=JobStatus.PENDING,
        )
        assert job.job_type == JobType.TEST
        assert job.params == {"key": "value"}
        assert job.priority == 1
        assert job.status == JobStatus.PENDING

    def test_job_repr(self):
        job = Job(id=uuid7(), job_type=JobType.TEST, status=JobStatus.PENDING)
        assert "TEST" in repr(job) or "test" in repr(job)
        assert "pending" in repr(job) or "PENDING" in repr(job)


class TestJobCRUD:
    """Test Job CRUD operations against a real test database."""

    def test_create_job(self, db_session):
        with patch("symbology.database.jobs.get_db_session", return_value=db_session):
            job = create_job(JobType.TEST, params={"ticker": "AAPL"}, priority=1)
            assert job.id is not None
            assert job.job_type == JobType.TEST
            assert job.params == {"ticker": "AAPL"}
            assert job.priority == 1
            assert job.status == JobStatus.PENDING
            assert job.max_retries == 3

    def test_get_job(self, db_session):
        with patch("symbology.database.jobs.get_db_session", return_value=db_session):
            created = create_job(JobType.TEST)
            fetched = get_job(created.id)
            assert fetched is not None
            assert fetched.id == created.id

    def test_get_job_not_found(self, db_session):
        with patch("symbology.database.jobs.get_db_session", return_value=db_session):
            result = get_job(uuid7())
            assert result is None

    def test_list_jobs_no_filter(self, db_session):
        with patch("symbology.database.jobs.get_db_session", return_value=db_session):
            create_job(JobType.TEST, params={"n": 1})
            create_job(JobType.COMPANY_INGESTION, params={"n": 2})
            jobs = list_jobs()
            assert len(jobs) >= 2

    def test_list_jobs_filter_by_status(self, db_session):
        with patch("symbology.database.jobs.get_db_session", return_value=db_session):
            create_job(JobType.TEST)
            jobs = list_jobs(status=JobStatus.PENDING)
            assert all(j.status == JobStatus.PENDING for j in jobs)

    def test_list_jobs_filter_by_type(self, db_session):
        with patch("symbology.database.jobs.get_db_session", return_value=db_session):
            create_job(JobType.TEST)
            create_job(JobType.COMPANY_INGESTION)
            jobs = list_jobs(job_type=JobType.TEST)
            assert all(j.job_type == JobType.TEST for j in jobs)

    def test_cancel_pending_job(self, db_session):
        with patch("symbology.database.jobs.get_db_session", return_value=db_session):
            job = create_job(JobType.TEST)
            cancelled = cancel_job(job.id)
            assert cancelled is not None
            assert cancelled.status == JobStatus.CANCELLED

    def test_cancel_non_pending_job_returns_none(self, db_session):
        with patch("symbology.database.jobs.get_db_session", return_value=db_session):
            job = create_job(JobType.TEST)
            # Move to in_progress so it can't be cancelled
            job.status = JobStatus.IN_PROGRESS
            db_session.commit()
            result = cancel_job(job.id)
            assert result is None

    def test_cancel_nonexistent_job_returns_none(self, db_session):
        with patch("symbology.database.jobs.get_db_session", return_value=db_session):
            result = cancel_job(uuid7())
            assert result is None


class TestClaimNextJob:
    """Test the atomic claim mechanism."""

    def test_claim_returns_highest_priority(self, db_session):
        with patch("symbology.database.jobs.get_db_session", return_value=db_session):
            create_job(JobType.TEST, params={"name": "low"}, priority=3)
            create_job(JobType.TEST, params={"name": "high"}, priority=0)
            create_job(JobType.TEST, params={"name": "medium"}, priority=2)
            claimed = claim_next_job("worker-1")
            assert claimed is not None
            assert claimed.params["name"] == "high"
            assert claimed.status == JobStatus.IN_PROGRESS
            assert claimed.worker_id == "worker-1"

    def test_claim_respects_fifo_within_priority(self, db_session):
        with patch("symbology.database.jobs.get_db_session", return_value=db_session):
            j1 = create_job(JobType.TEST, params={"order": 1}, priority=2)
            j2 = create_job(JobType.TEST, params={"order": 2}, priority=2)
            claimed = claim_next_job("worker-1")
            assert claimed.id == j1.id

    def test_claim_returns_none_when_empty(self, db_session):
        with patch("symbology.database.jobs.get_db_session", return_value=db_session):
            result = claim_next_job("worker-1")
            assert result is None


class TestCompleteAndFail:
    """Test job completion and failure flows."""

    def test_complete_job(self, db_session):
        with patch("symbology.database.jobs.get_db_session", return_value=db_session):
            job = create_job(JobType.TEST)
            job.status = JobStatus.IN_PROGRESS
            job.started_at = datetime.now(timezone.utc).replace(tzinfo=None)
            db_session.commit()
            completed = complete_job(job.id, result={"output": "done"})
            assert completed.status == JobStatus.COMPLETED
            assert completed.result == {"output": "done"}

    def test_complete_nonexistent_returns_none(self, db_session):
        with patch("symbology.database.jobs.get_db_session", return_value=db_session):
            result = complete_job(uuid7())
            assert result is None

    def test_fail_job_with_retries_remaining(self, db_session):
        with patch("symbology.database.jobs.get_db_session", return_value=db_session):
            job = create_job(JobType.TEST, max_retries=3)
            job.status = JobStatus.IN_PROGRESS
            db_session.commit()
            failed = fail_job(job.id, error="timeout")
            assert failed.status == JobStatus.PENDING  # re-queued
            assert failed.retry_count == 1
            assert failed.error == "timeout"
            assert failed.worker_id is None

    def test_fail_job_exhausts_retries(self, db_session):
        with patch("symbology.database.jobs.get_db_session", return_value=db_session):
            job = create_job(JobType.TEST, max_retries=1)
            job.status = JobStatus.IN_PROGRESS
            job.retry_count = 0
            db_session.commit()
            failed = fail_job(job.id, error="fatal")
            assert failed.status == JobStatus.FAILED

    def test_fail_nonexistent_returns_none(self, db_session):
        with patch("symbology.database.jobs.get_db_session", return_value=db_session):
            result = fail_job(uuid7(), error="nope")
            assert result is None


class TestStaleDetection:
    """Test stale job recovery."""

    def test_mark_stale_jobs(self, db_session):
        with patch("symbology.database.jobs.get_db_session", return_value=db_session):
            job = create_job(JobType.TEST, max_retries=3)
            # Simulate stale: set to IN_PROGRESS with old updated_at
            job.status = JobStatus.IN_PROGRESS
            job.updated_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=700)
            db_session.commit()
            stale = mark_stale_jobs_as_failed(stale_threshold_seconds=600)
            assert len(stale) == 1
            assert stale[0].id == job.id
            # With retries remaining, should be re-queued
            assert stale[0].status == JobStatus.PENDING

    def test_no_stale_jobs(self, db_session):
        with patch("symbology.database.jobs.get_db_session", return_value=db_session):
            # Fresh pending job should not be stale
            create_job(JobType.TEST)
            stale = mark_stale_jobs_as_failed(stale_threshold_seconds=600)
            assert len(stale) == 0


class TestRequeueFailedJobs:
    """Test requeue and cancel operations on failed jobs."""

    def test_requeue_resets_status_and_fields(self, db_session):
        with patch("symbology.database.jobs.get_db_session", return_value=db_session):
            job = create_job(JobType.BULK_INGEST, max_retries=3)
            job.status = JobStatus.FAILED
            job.retry_count = 3
            job.worker_id = "worker-1"
            job.error = "connection timeout"
            job.started_at = datetime.now(timezone.utc).replace(tzinfo=None)
            job.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
            db_session.commit()

            requeued = requeue_failed_jobs()
            assert len(requeued) == 1
            assert requeued[0].status == JobStatus.PENDING
            assert requeued[0].retry_count == 0
            assert requeued[0].worker_id is None
            assert requeued[0].error is None
            assert requeued[0].started_at is None
            assert requeued[0].completed_at is None

    def test_requeue_filters_by_type(self, db_session):
        with patch("symbology.database.jobs.get_db_session", return_value=db_session):
            j1 = create_job(JobType.BULK_INGEST)
            j1.status = JobStatus.FAILED
            j2 = create_job(JobType.TEST)
            j2.status = JobStatus.FAILED
            db_session.commit()

            requeued = requeue_failed_jobs(job_type=JobType.BULK_INGEST)
            assert len(requeued) == 1
            assert requeued[0].job_type == JobType.BULK_INGEST
            # The TEST job should still be FAILED
            db_session.refresh(j2)
            assert j2.status == JobStatus.FAILED

    def test_requeue_no_failed_jobs(self, db_session):
        with patch("symbology.database.jobs.get_db_session", return_value=db_session):
            create_job(JobType.TEST)  # PENDING, not FAILED
            requeued = requeue_failed_jobs()
            assert len(requeued) == 0


class TestCancelFailedJobs:

    def test_cancel_failed_jobs(self, db_session):
        with patch("symbology.database.jobs.get_db_session", return_value=db_session):
            j1 = create_job(JobType.BULK_INGEST)
            j1.status = JobStatus.FAILED
            j2 = create_job(JobType.BULK_INGEST)
            j2.status = JobStatus.FAILED
            db_session.commit()

            count = cancel_failed_jobs()
            assert count == 2
            db_session.refresh(j1)
            db_session.refresh(j2)
            assert j1.status == JobStatus.CANCELLED
            assert j2.status == JobStatus.CANCELLED

    def test_cancel_filters_by_type(self, db_session):
        with patch("symbology.database.jobs.get_db_session", return_value=db_session):
            j1 = create_job(JobType.BULK_INGEST)
            j1.status = JobStatus.FAILED
            j2 = create_job(JobType.TEST)
            j2.status = JobStatus.FAILED
            db_session.commit()

            count = cancel_failed_jobs(job_type=JobType.BULK_INGEST)
            assert count == 1
            db_session.refresh(j2)
            assert j2.status == JobStatus.FAILED  # untouched

    def test_cancel_no_failed_jobs(self, db_session):
        with patch("symbology.database.jobs.get_db_session", return_value=db_session):
            count = cancel_failed_jobs()
            assert count == 0


class TestCountJobsByStatus:

    def test_count_failed(self, db_session):
        with patch("symbology.database.jobs.get_db_session", return_value=db_session):
            j1 = create_job(JobType.BULK_INGEST)
            j1.status = JobStatus.FAILED
            j2 = create_job(JobType.TEST)
            j2.status = JobStatus.FAILED
            create_job(JobType.TEST)  # PENDING
            db_session.commit()

            assert count_jobs_by_status(JobStatus.FAILED) == 2
            assert count_jobs_by_status(JobStatus.FAILED, job_type=JobType.BULK_INGEST) == 1
            assert count_jobs_by_status(JobStatus.PENDING) == 1
