"""Tests for the scheduler main loop."""
import signal
from unittest.mock import MagicMock, patch

from symbology.scheduler.main import run_scheduler


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
            patch("symbology.scheduler.alerts.check_alerts"),
            patch("signal.signal", side_effect=fake_signal),
        ):
            run_scheduler()

        # The loop should have run 0 times since shutdown was requested immediately
        assert call_count == 0
