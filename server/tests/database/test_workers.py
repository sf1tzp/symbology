"""Tests for the first-class worker registry and its reap/reclaim sweep."""
from datetime import datetime, timedelta, timezone

import pytest

from symbology.database.jobs import JobStatus, JobType, create_job
from symbology.database.workers import (
    Worker,
    WorkerStatus,
    heartbeat_worker,
    list_live_workers,
    mark_worker_stopped,
    reap_dead_workers,
    register_worker,
)

pytestmark = pytest.mark.integration


def _age_heartbeat(session, worker_id: str, seconds: int) -> None:
    """Backdate a worker's heartbeat to simulate it having gone quiet."""
    w = session.query(Worker).filter(Worker.id == worker_id).first()
    w.last_heartbeat = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=seconds)
    session.commit()


def _in_progress_job(worker_id: str, retry_count: int = 0):
    """A job already claimed by ``worker_id`` (IN_PROGRESS)."""
    job = create_job(JobType.TEST)
    job.status = JobStatus.IN_PROGRESS
    job.worker_id = worker_id
    job.retry_count = retry_count
    return job


class TestRegisterWorker:
    def test_creates_row_as_idle_and_fresh(self, db_session):
        register_worker("w1", hostname="host-a", pid=123)
        w = db_session.query(Worker).filter(Worker.id == "w1").first()
        assert w is not None
        assert w.status == WorkerStatus.IDLE
        assert w.hostname == "host-a"
        assert w.pid == 123
        assert w.current_job_id is None

    def test_is_idempotent_on_restart(self, db_session):
        register_worker("w1", hostname="host-a", pid=1)
        # A restart re-registers the same id: reset in place, not duplicated.
        register_worker("w1", hostname="host-a", pid=2)
        rows = db_session.query(Worker).filter(Worker.id == "w1").all()
        assert len(rows) == 1
        assert rows[0].pid == 2
        assert rows[0].status == WorkerStatus.IDLE


class TestHeartbeatWorker:
    def test_updates_status_and_current_job(self, db_session):
        register_worker("w1")
        job = _in_progress_job("w1")
        db_session.commit()
        assert heartbeat_worker("w1", status=WorkerStatus.RUNNING, current_job_id=job.id) is True
        w = db_session.query(Worker).filter(Worker.id == "w1").first()
        assert w.status == WorkerStatus.RUNNING
        assert str(w.current_job_id) == str(job.id)

    def test_returns_false_for_unknown_worker(self, db_session):
        assert heartbeat_worker("ghost", status=WorkerStatus.RUNNING) is False


class TestMarkWorkerStopped:
    def test_marks_stopped_and_clears_job(self, db_session):
        register_worker("w1")
        heartbeat_worker("w1", status=WorkerStatus.RUNNING, current_job_id=None)
        mark_worker_stopped("w1")
        w = db_session.query(Worker).filter(Worker.id == "w1").first()
        assert w.status == WorkerStatus.STOPPED
        assert w.current_job_id is None


class TestReapDeadWorkers:
    def test_lapsed_worker_marked_dead_and_job_reclaimed_without_burning_retry(self, db_session):
        register_worker("w1")
        job = _in_progress_job("w1", retry_count=2)
        db_session.commit()
        _age_heartbeat(db_session, "w1", seconds=200)

        reclaimed = reap_dead_workers(stale_threshold_seconds=90)

        assert [j.id for j in reclaimed] == [job.id]
        db_session.refresh(job)
        # Operational requeue: back on the queue, owner cleared, retry budget intact.
        assert job.status == JobStatus.PENDING
        assert job.worker_id is None
        assert job.started_at is None
        assert job.retry_count == 2  # <-- the whole point: a dead worker isn't the job's fault

        w = db_session.query(Worker).filter(Worker.id == "w1").first()
        assert w.status == WorkerStatus.DEAD

    def test_live_workers_jobs_are_left_alone(self, db_session):
        register_worker("w1")
        # Fresh heartbeat → worker is live, so its in-progress job must be untouched.
        heartbeat_worker("w1", status=WorkerStatus.RUNNING)
        job = _in_progress_job("w1")
        db_session.commit()

        reclaimed = reap_dead_workers(stale_threshold_seconds=90)

        assert reclaimed == []
        db_session.refresh(job)
        assert job.status == JobStatus.IN_PROGRESS
        assert job.worker_id == "w1"

    def test_reclaims_job_of_unregistered_worker(self, db_session):
        # A job whose owner never registered (or whose row is gone) has no live
        # worker, so it's reclaimed too — covers the orphan case without any
        # job-level staleness heuristic.
        job = _in_progress_job("ghost-worker")
        db_session.commit()

        reclaimed = reap_dead_workers(stale_threshold_seconds=90)

        assert [j.id for j in reclaimed] == [job.id]
        db_session.refresh(job)
        assert job.status == JobStatus.PENDING
        assert job.worker_id is None


class TestListLiveWorkers:
    def test_excludes_stale_and_stopped(self, db_session):
        register_worker("live")
        register_worker("stale")
        register_worker("gone")
        mark_worker_stopped("gone")
        _age_heartbeat(db_session, "stale", seconds=200)

        live = list_live_workers(stale_threshold_seconds=90)
        assert [w.id for w in live] == ["live"]
