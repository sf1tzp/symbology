"""Tests for the scheduler main loop."""
import signal
from unittest.mock import MagicMock, patch

from symbology.scheduler.main import _detect_stale_runs, run_scheduler


class TestDetectStaleRuns:
    def test_warns_on_stale_run(self):
        from datetime import datetime, timedelta, timezone

        mock_run = MagicMock()
        mock_run.id = "run-1"
        mock_run.company_id = "comp-1"
        mock_run.started_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=3)

        with patch("symbology.scheduler.main.list_pipeline_runs", return_value=[mock_run]) as mock_list:
            _detect_stale_runs(threshold_seconds=7200)

        mock_list.assert_called_once()

    def test_no_warning_for_fresh_run(self):
        from datetime import datetime, timezone

        mock_run = MagicMock()
        mock_run.id = "run-2"
        mock_run.started_at = datetime.now(timezone.utc).replace(tzinfo=None)

        with patch("symbology.scheduler.main.list_pipeline_runs", return_value=[mock_run]):
            # Should not raise or warn
            _detect_stale_runs(threshold_seconds=7200)


class TestRunScheduler:
    def test_graceful_shutdown(self):
        """Test that the scheduler loop exits on signal."""
        call_count = 0

        def fake_poll(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return 0

        def fake_signal(signum, handler):
            # Immediately request shutdown when SIGTERM handler is registered
            if signum == signal.SIGTERM:
                handler(signum, None)

        with (
            patch("symbology.scheduler.main.configure_logging"),
            patch("symbology.scheduler.main.init_db"),
            patch("symbology.scheduler.main.poll_all_companies", side_effect=fake_poll),
            patch("symbology.scheduler.main._detect_stale_runs"),
            patch("signal.signal", side_effect=fake_signal),
        ):
            run_scheduler()

        # The loop should have run 0 times since shutdown was requested immediately
        assert call_count == 0
