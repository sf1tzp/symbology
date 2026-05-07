"""Tests for the pipeline_runs database module."""
from unittest.mock import patch

from uuid_extensions import uuid7
import pytest

from symbology.database.pipeline_runs import (
    PipelineRun,
    PipelineRunStatus,
    PipelineTrigger,
    complete_pipeline_run,
    create_pipeline_run,
    fail_pipeline_run,
    get_pipeline_run,
    list_pipeline_runs,
    start_pipeline_run,
)


pytestmark = pytest.mark.integration


@pytest.fixture
def company_id(db_session):
    """Create a minimal company row and return its UUID."""
    from symbology.database.companies import Company
    company = Company(name="Test Corp", ticker="TEST")
    db_session.add(company)
    db_session.commit()
    return company.id


class TestPipelineRunModel:
    """Test the PipelineRun ORM model."""

    def test_create_instance(self):
        run = PipelineRun(
            company_id=uuid7(),
            trigger=PipelineTrigger.MANUAL,
            status=PipelineRunStatus.PENDING,
            forms=["10-K", "10-Q"],
        )
        assert run.trigger == PipelineTrigger.MANUAL
        assert run.status == PipelineRunStatus.PENDING
        assert run.forms == ["10-K", "10-Q"]

    def test_repr(self):
        cid = uuid7()
        run = PipelineRun(
            id=uuid7(), company_id=cid, status=PipelineRunStatus.RUNNING,
        )
        assert "PipelineRun" in repr(run)
        assert "running" in repr(run)

    def test_enum_values(self):
        assert PipelineTrigger.MANUAL.value == "manual"
        assert PipelineTrigger.SCHEDULED.value == "scheduled"
        assert PipelineRunStatus.PARTIAL.value == "partial"


class TestPipelineRunCRUD:
    """Test PipelineRun CRUD operations against a real test database."""

    def test_create_pipeline_run(self, db_session, company_id):
        with patch("symbology.database.pipeline_runs.get_db_session", return_value=db_session):
            run = create_pipeline_run(
                company_id=company_id,
                forms=["10-K"],
                trigger=PipelineTrigger.MANUAL,
                run_metadata={"ticker": "TEST"},
            )
            assert run.id is not None
            assert run.company_id == company_id
            assert run.forms == ["10-K"]
            assert run.trigger == PipelineTrigger.MANUAL
            assert run.status == PipelineRunStatus.PENDING
            assert run.run_metadata == {"ticker": "TEST"}

    def test_create_pipeline_run_string_company_id(self, db_session, company_id):
        with patch("symbology.database.pipeline_runs.get_db_session", return_value=db_session):
            run = create_pipeline_run(
                company_id=str(company_id),
                forms=["10-Q"],
            )
            assert run.company_id == company_id

    def test_get_pipeline_run(self, db_session, company_id):
        with patch("symbology.database.pipeline_runs.get_db_session", return_value=db_session):
            created = create_pipeline_run(company_id=company_id, forms=["10-K"])
            fetched = get_pipeline_run(created.id)
            assert fetched is not None
            assert fetched.id == created.id

    def test_get_pipeline_run_not_found(self, db_session):
        with patch("symbology.database.pipeline_runs.get_db_session", return_value=db_session):
            result = get_pipeline_run(uuid7())
            assert result is None

    def test_list_pipeline_runs_no_filter(self, db_session, company_id):
        with patch("symbology.database.pipeline_runs.get_db_session", return_value=db_session):
            create_pipeline_run(company_id=company_id, forms=["10-K"])
            create_pipeline_run(company_id=company_id, forms=["10-Q"])
            runs = list_pipeline_runs()
            assert len(runs) >= 2

    def test_list_pipeline_runs_filter_by_company(self, db_session, company_id):
        with patch("symbology.database.pipeline_runs.get_db_session", return_value=db_session):
            create_pipeline_run(company_id=company_id, forms=["10-K"])
            runs = list_pipeline_runs(company_id=company_id)
            assert all(r.company_id == company_id for r in runs)

    def test_list_pipeline_runs_filter_by_status(self, db_session, company_id):
        with patch("symbology.database.pipeline_runs.get_db_session", return_value=db_session):
            create_pipeline_run(company_id=company_id, forms=["10-K"])
            runs = list_pipeline_runs(status=PipelineRunStatus.PENDING)
            assert all(r.status == PipelineRunStatus.PENDING for r in runs)

    def test_start_pipeline_run(self, db_session, company_id):
        with patch("symbology.database.pipeline_runs.get_db_session", return_value=db_session):
            run = create_pipeline_run(company_id=company_id, forms=["10-K"])
            started = start_pipeline_run(run.id)
            assert started is not None
            assert started.status == PipelineRunStatus.RUNNING

    def test_start_pipeline_run_not_found(self, db_session):
        with patch("symbology.database.pipeline_runs.get_db_session", return_value=db_session):
            result = start_pipeline_run(uuid7())
            assert result is None

    def test_complete_pipeline_run_all_success(self, db_session, company_id):
        with patch("symbology.database.pipeline_runs.get_db_session", return_value=db_session):
            run = create_pipeline_run(company_id=company_id, forms=["10-K"])
            start_pipeline_run(run.id)
            completed = complete_pipeline_run(
                run.id, jobs_created=5, jobs_completed=5, jobs_failed=0,
            )
            assert completed.status == PipelineRunStatus.COMPLETED
            assert completed.jobs_created == 5
            assert completed.jobs_completed == 5
            assert completed.jobs_failed == 0

    def test_complete_pipeline_run_partial(self, db_session, company_id):
        with patch("symbology.database.pipeline_runs.get_db_session", return_value=db_session):
            run = create_pipeline_run(company_id=company_id, forms=["10-K"])
            start_pipeline_run(run.id)
            completed = complete_pipeline_run(
                run.id, jobs_created=5, jobs_completed=3, jobs_failed=2,
            )
            assert completed.status == PipelineRunStatus.PARTIAL
            assert completed.jobs_failed == 2

    def test_complete_pipeline_run_not_found(self, db_session):
        with patch("symbology.database.pipeline_runs.get_db_session", return_value=db_session):
            result = complete_pipeline_run(uuid7())
            assert result is None

    def test_fail_pipeline_run(self, db_session, company_id):
        with patch("symbology.database.pipeline_runs.get_db_session", return_value=db_session):
            run = create_pipeline_run(company_id=company_id, forms=["10-K"])
            start_pipeline_run(run.id)
            failed = fail_pipeline_run(
                run.id, error="Connection timeout",
                jobs_created=3, jobs_completed=1, jobs_failed=2,
            )
            assert failed.status == PipelineRunStatus.FAILED
            assert failed.error == "Connection timeout"
            assert failed.jobs_created == 3

    def test_fail_pipeline_run_not_found(self, db_session):
        with patch("symbology.database.pipeline_runs.get_db_session", return_value=db_session):
            result = fail_pipeline_run(uuid7(), error="nope")
            assert result is None
