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
    get_active_jobs,
    get_job,
    heartbeat_job,
    list_jobs,
    mark_stale_jobs_as_failed,
    requeue_failed_jobs,
    requeue_job,
    requeue_job_for_shutdown,
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

    def test_claim_skips_future_scheduled_job(self, db_session):
        with patch("symbology.database.jobs.get_db_session", return_value=db_session):
            future = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=10)
            create_job(JobType.TEST, params={"name": "deferred"}, priority=0,
                       scheduled_at=future)
            # Highest priority but not yet eligible — nothing else pending.
            assert claim_next_job("worker-1") is None

    def test_claim_returns_due_scheduled_job(self, db_session):
        with patch("symbology.database.jobs.get_db_session", return_value=db_session):
            past = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=1)
            j = create_job(JobType.TEST, params={"name": "due"}, priority=2,
                           scheduled_at=past)
            claimed = claim_next_job("worker-1")
            assert claimed is not None and claimed.id == j.id

    def test_claim_prefers_eligible_over_future(self, db_session):
        with patch("symbology.database.jobs.get_db_session", return_value=db_session):
            future = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=10)
            create_job(JobType.TEST, params={"name": "deferred"}, priority=0,
                       scheduled_at=future)
            now_job = create_job(JobType.TEST, params={"name": "now"}, priority=3)
            claimed = claim_next_job("worker-1")
            # The lower-priority job wins because the priority-0 one isn't due.
            assert claimed.id == now_job.id


class TestGetActiveJobs:
    """Test the in-flight (PENDING/IN_PROGRESS) lookup used for dependency gating."""

    def test_returns_pending_and_in_progress_only(self, db_session):
        with patch("symbology.database.jobs.get_db_session", return_value=db_session):
            pending = create_job(JobType.FILING_PAGE_CONTENT, params={"year": 2024})
            running = create_job(JobType.FILING_PAGE_CONTENT, params={"year": 2023})
            claim_next_job("worker-1")  # flips one to IN_PROGRESS
            done = create_job(JobType.FILING_PAGE_CONTENT, params={"year": 2022})
            complete_job(done.id)
            create_job(JobType.TEST, params={"year": 2024})  # different type, excluded

            active = get_active_jobs(JobType.FILING_PAGE_CONTENT)
            ids = {j.id for j in active}
            assert pending.id in ids and running.id in ids
            assert done.id not in ids
            assert all(j.job_type == JobType.FILING_PAGE_CONTENT for j in active)


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

    def test_heartbeat_keeps_job_from_going_stale(self, db_session):
        with patch("symbology.database.jobs.get_db_session", return_value=db_session):
            job = create_job(JobType.TEST, max_retries=3)
            job.status = JobStatus.IN_PROGRESS
            job.worker_id = "w1"
            # Older than the threshold — would be reclaimed without a heartbeat.
            job.updated_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=700)
            db_session.commit()

            assert heartbeat_job(job.id, "w1") is True

            stale = mark_stale_jobs_as_failed(stale_threshold_seconds=600)
            assert stale == []
            db_session.refresh(job)
            assert job.status == JobStatus.IN_PROGRESS

    def test_heartbeat_ignores_jobs_owned_by_another_worker(self, db_session):
        with patch("symbology.database.jobs.get_db_session", return_value=db_session):
            job = create_job(JobType.TEST)
            job.status = JobStatus.IN_PROGRESS
            job.worker_id = "owner"
            old = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=700)
            job.updated_at = old
            db_session.commit()

            # A worker that no longer owns the claim must not revive the row.
            assert heartbeat_job(job.id, "stranger") is False
            db_session.refresh(job)
            assert job.updated_at == old


class TestRequeueForShutdown:
    """Test the shutdown requeue path used by the worker."""

    def test_requeue_resets_without_consuming_retry(self, db_session):
        with patch("symbology.database.jobs.get_db_session", return_value=db_session):
            job = create_job(JobType.TEST, max_retries=3)
            job.status = JobStatus.IN_PROGRESS
            job.worker_id = "w1"
            job.retry_count = 1
            db_session.commit()

            result = requeue_job_for_shutdown(job.id)
            assert result.status == JobStatus.PENDING
            assert result.worker_id is None
            assert result.started_at is None
            # An operational restart must NOT count against the retry budget.
            assert result.retry_count == 1

    def test_requeue_is_idempotent(self, db_session):
        with patch("symbology.database.jobs.get_db_session", return_value=db_session):
            job = create_job(JobType.TEST, max_retries=3)
            job.status = JobStatus.IN_PROGRESS
            job.retry_count = 2
            db_session.commit()

            requeue_job_for_shutdown(job.id)
            # Second call (e.g. the worker thread after the main loop) is a no-op.
            again = requeue_job_for_shutdown(job.id)
            assert again.status == JobStatus.PENDING
            assert again.retry_count == 2

    def test_requeue_nonexistent_returns_none(self, db_session):
        with patch("symbology.database.jobs.get_db_session", return_value=db_session):
            assert requeue_job_for_shutdown(uuid7()) is None


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

    def test_requeue_single_job_resets_fields(self, db_session):
        with patch("symbology.database.jobs.get_db_session", return_value=db_session):
            job = create_job(JobType.BULK_INGEST, max_retries=3)
            job.status = JobStatus.FAILED
            job.retry_count = 3
            job.worker_id = "worker-1"
            job.error = "connection timeout"
            job.started_at = datetime.now(timezone.utc).replace(tzinfo=None)
            job.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
            db_session.commit()

            requeued = requeue_job(job.id)
            assert requeued is not None
            assert requeued.status == JobStatus.PENDING
            assert requeued.retry_count == 0
            assert requeued.worker_id is None
            assert requeued.error is None
            assert requeued.started_at is None
            assert requeued.completed_at is None

    def test_requeue_single_job_only_affects_target(self, db_session):
        with patch("symbology.database.jobs.get_db_session", return_value=db_session):
            j1 = create_job(JobType.BULK_INGEST)
            j1.status = JobStatus.FAILED
            j2 = create_job(JobType.TEST)
            j2.status = JobStatus.FAILED
            db_session.commit()

            requeue_job(j1.id)
            db_session.refresh(j2)
            assert j2.status == JobStatus.FAILED

    def test_requeue_single_job_not_failed_returns_none(self, db_session):
        with patch("symbology.database.jobs.get_db_session", return_value=db_session):
            job = create_job(JobType.TEST)  # PENDING, not FAILED
            assert requeue_job(job.id) is None

    def test_requeue_single_job_nonexistent_returns_none(self, db_session):
        with patch("symbology.database.jobs.get_db_session", return_value=db_session):
            assert requeue_job(uuid7()) is None


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
