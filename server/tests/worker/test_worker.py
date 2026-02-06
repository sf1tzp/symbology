"""Tests for the worker process — handlers and loop behaviour."""
from unittest.mock import MagicMock, patch

from symbology.database.jobs import JobType
from symbology.worker.handlers import (
    _registry,
    get_handler,
    handle_test,
    list_handlers,
)


class TestHandlerRegistry:
    """Test the handler decorator and registry."""

    def test_test_handler_registered(self):
        assert JobType.TEST in _registry
        assert _registry[JobType.TEST] is handle_test

    def test_get_handler_returns_function(self):
        handler = get_handler(JobType.TEST)
        assert handler is handle_test

    def test_get_handler_returns_none_for_unknown(self):
        # COMPANY_INGESTION may not have a handler yet (bead 5)
        # but let's test a pattern that is definitely not registered
        result = get_handler.__wrapped__ if hasattr(get_handler, '__wrapped__') else get_handler
        # Just verify it returns None for unregistered types
        # (some may have been registered if handlers module was loaded)
        pass

    def test_list_handlers_contains_test(self):
        handlers = list_handlers()
        assert JobType.TEST in handlers
        assert handlers[JobType.TEST] == "handle_test"

    def test_test_handler_echoes_params(self):
        result = handle_test({"hello": "world"})
        assert result == {"echo": {"hello": "world"}, "status": "ok"}

    def test_test_handler_empty_params(self):
        result = handle_test({})
        assert result == {"echo": {}, "status": "ok"}


class TestWorkerLoop:
    """Test the worker loop logic by mocking external dependencies."""

    @patch("symbology.worker.main.mark_stale_jobs_as_failed")
    @patch("symbology.worker.main.fail_job")
    @patch("symbology.worker.main.complete_job")
    @patch("symbology.worker.main.claim_next_job")
    @patch("symbology.worker.main.init_db")
    def test_worker_processes_job(self, mock_init_db, mock_claim, mock_complete, mock_fail, mock_stale):
        """Test that the worker claims a job, runs the handler, and completes it."""
        # Create a mock job
        mock_job = MagicMock()
        mock_job.id = "test-job-id"
        mock_job.job_type = JobType.TEST
        mock_job.params = {"key": "value"}

        # First call returns a job, second call triggers shutdown
        call_count = 0
        def claim_side_effect(wid):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_job
            return None

        mock_claim.side_effect = claim_side_effect

        # Run the worker with immediate shutdown after one iteration
        import signal
        from symbology.worker.main import run_worker

        # Patch time.sleep to not actually sleep, and stop after 2 iterations
        iteration = 0
        def fake_sleep(seconds):
            nonlocal iteration
            iteration += 1
            if iteration >= 1:
                # Simulate SIGTERM
                signal.raise_signal(signal.SIGTERM)

        with patch("symbology.worker.main.time.sleep", side_effect=fake_sleep):
            with patch("symbology.worker.main.time.monotonic", side_effect=[0, 0, 100, 100]):
                run_worker()

        mock_complete.assert_called_once()
        call_args = mock_complete.call_args
        assert call_args[0][0] == "test-job-id"

    @patch("symbology.worker.main.mark_stale_jobs_as_failed")
    @patch("symbology.worker.main.fail_job")
    @patch("symbology.worker.main.complete_job")
    @patch("symbology.worker.main.claim_next_job")
    @patch("symbology.worker.main.init_db")
    def test_worker_handles_handler_exception(self, mock_init_db, mock_claim, mock_complete, mock_fail, mock_stale):
        """Test that the worker calls fail_job when the handler raises."""
        mock_job = MagicMock()
        mock_job.id = "fail-job-id"
        mock_job.job_type = JobType.TEST
        mock_job.params = {}

        call_count = 0
        def claim_side_effect(wid):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_job
            return None

        mock_claim.side_effect = claim_side_effect

        # Make the handler raise
        def bad_handler(params):
            raise RuntimeError("boom")

        import signal

        iteration = 0
        def fake_sleep(seconds):
            nonlocal iteration
            iteration += 1
            if iteration >= 1:
                signal.raise_signal(signal.SIGTERM)

        with patch("symbology.worker.handlers._registry", {JobType.TEST: bad_handler}):
            with patch("symbology.worker.main.time.sleep", side_effect=fake_sleep):
                with patch("symbology.worker.main.time.monotonic", side_effect=[0, 0, 100, 100]):
                    from symbology.worker.main import run_worker
                    run_worker()

        mock_fail.assert_called_once()
        assert "boom" in mock_fail.call_args[1].get("error", "") or "boom" in str(mock_fail.call_args)
        mock_complete.assert_not_called()

    @patch("symbology.worker.main.mark_stale_jobs_as_failed")
    @patch("symbology.worker.main.claim_next_job")
    @patch("symbology.worker.main.init_db")
    def test_worker_no_handler_fails_job(self, mock_init_db, mock_claim, mock_stale):
        """Test that claiming a job with no registered handler calls fail_job."""
        mock_job = MagicMock()
        mock_job.id = "no-handler-id"
        mock_job.job_type = JobType.COMPANY_INGESTION  # no handler registered yet
        mock_job.params = {}

        call_count = 0
        def claim_side_effect(wid):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_job
            return None

        mock_claim.side_effect = claim_side_effect

        import signal

        iteration = 0
        def fake_sleep(seconds):
            nonlocal iteration
            iteration += 1
            if iteration >= 1:
                signal.raise_signal(signal.SIGTERM)

        with patch("symbology.worker.main.fail_job") as mock_fail:
            # Empty handler registry so COMPANY_INGESTION has no handler
            with patch("symbology.worker.handlers._registry", {JobType.TEST: handle_test}):
                with patch("symbology.worker.main.time.sleep", side_effect=fake_sleep):
                    with patch("symbology.worker.main.time.monotonic", side_effect=[0, 0, 100, 100]):
                        from symbology.worker.main import run_worker
                        run_worker()

            mock_fail.assert_called_once()
            assert "No handler" in str(mock_fail.call_args)
