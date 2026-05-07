"""Tests for the scheduler alerts module."""
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from symbology.database.companies import Company
from symbology.database.pipeline_runs import PipelineRun, PipelineRunStatus, PipelineTrigger
from symbology.scheduler.alerts import (
    check_alerts,
    detect_consecutive_failures,
    detect_stale_runs,
    send_webhook,
)
from uuid_extensions import uuid7

SAMPLE_COMPANY_ID = uuid7()
SAMPLE_RUN_ID = uuid7()

SAMPLE_COMPANY = Company(
    id=SAMPLE_COMPANY_ID,
    name="Acme Corp",
    ticker="ACME",
    exchanges=["NYSE"],
)


def _make_run(status=PipelineRunStatus.COMPLETED, started_at=None):
    return PipelineRun(
        id=uuid7(),
        company_id=SAMPLE_COMPANY_ID,
        trigger=PipelineTrigger.SCHEDULED,
        status=status,
        forms=["10-K"],
        started_at=started_at or datetime(2025, 1, 1, 12, 0, 0),
        jobs_created=1,
        jobs_completed=1 if status == PipelineRunStatus.COMPLETED else 0,
        jobs_failed=1 if status == PipelineRunStatus.FAILED else 0,
        run_metadata={},
    )


class TestDetectConsecutiveFailures:

    @patch("symbology.scheduler.alerts.get_company")
    @patch("symbology.scheduler.alerts.count_consecutive_failures")
    @patch("symbology.scheduler.alerts.get_latest_run_per_company")
    def test_no_failures(self, mock_latest, mock_count, mock_company):
        mock_latest.return_value = [_make_run()]
        mock_count.return_value = 0
        mock_company.return_value = SAMPLE_COMPANY

        alerts = detect_consecutive_failures(threshold=3)
        assert alerts == []

    @patch("symbology.scheduler.alerts.get_company")
    @patch("symbology.scheduler.alerts.count_consecutive_failures")
    @patch("symbology.scheduler.alerts.get_latest_run_per_company")
    def test_failures_above_threshold(self, mock_latest, mock_count, mock_company):
        mock_latest.return_value = [_make_run(PipelineRunStatus.FAILED)]
        mock_count.return_value = 5
        mock_company.return_value = SAMPLE_COMPANY

        alerts = detect_consecutive_failures(threshold=3)
        assert len(alerts) == 1
        assert alerts[0]["ticker"] == "ACME"
        assert alerts[0]["consecutive_failures"] == 5

    @patch("symbology.scheduler.alerts.get_company")
    @patch("symbology.scheduler.alerts.count_consecutive_failures")
    @patch("symbology.scheduler.alerts.get_latest_run_per_company")
    def test_failures_below_threshold(self, mock_latest, mock_count, mock_company):
        mock_latest.return_value = [_make_run(PipelineRunStatus.FAILED)]
        mock_count.return_value = 2
        mock_company.return_value = SAMPLE_COMPANY

        alerts = detect_consecutive_failures(threshold=3)
        assert alerts == []


class TestDetectStaleRuns:

    @patch("symbology.scheduler.alerts.list_pipeline_runs")
    def test_no_stale_runs(self, mock_list):
        recent_run = _make_run(
            PipelineRunStatus.RUNNING,
            started_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        mock_list.return_value = [recent_run]

        alerts = detect_stale_runs(threshold_seconds=7200)
        assert alerts == []

    @patch("symbology.scheduler.alerts.list_pipeline_runs")
    def test_stale_run_detected(self, mock_list):
        old_start = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=3)
        stale_run = _make_run(PipelineRunStatus.RUNNING, started_at=old_start)
        mock_list.return_value = [stale_run]

        alerts = detect_stale_runs(threshold_seconds=7200)
        assert len(alerts) == 1
        assert alerts[0]["stale_seconds"] > 7200

    @patch("symbology.scheduler.alerts.list_pipeline_runs")
    def test_empty_running_list(self, mock_list):
        mock_list.return_value = []
        alerts = detect_stale_runs(threshold_seconds=7200)
        assert alerts == []


class TestSendWebhook:

    @patch("symbology.scheduler.alerts.httpx")
    def test_successful_webhook(self, mock_httpx):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_httpx.post.return_value = mock_response

        send_webhook("https://hooks.example.com/alert", {"test": True}, timeout=5)
        mock_httpx.post.assert_called_once_with(
            "https://hooks.example.com/alert",
            json={"test": True},
            timeout=5,
        )

    @patch("symbology.scheduler.alerts.httpx")
    def test_webhook_failure(self, mock_httpx):
        mock_httpx.post.side_effect = Exception("Connection refused")

        # Should not raise — logs the error instead
        send_webhook("https://hooks.example.com/alert", {"test": True})


class TestCheckAlerts:

    @patch("symbology.scheduler.alerts.send_webhook")
    @patch("symbology.scheduler.alerts.detect_stale_runs")
    @patch("symbology.scheduler.alerts.detect_consecutive_failures")
    def test_check_alerts_no_issues(self, mock_failures, mock_stale, mock_webhook):
        mock_failures.return_value = []
        mock_stale.return_value = []

        check_alerts()

        mock_webhook.assert_not_called()

    @patch("symbology.scheduler.alerts.scheduler_settings")
    @patch("symbology.scheduler.alerts.send_webhook")
    @patch("symbology.scheduler.alerts.detect_stale_runs")
    @patch("symbology.scheduler.alerts.detect_consecutive_failures")
    def test_check_alerts_sends_webhook(self, mock_failures, mock_stale, mock_webhook, mock_cfg):
        mock_cfg.alert_consecutive_failure_threshold = 3
        mock_cfg.alert_stale_run_threshold_seconds = 7200
        mock_cfg.alert_webhook_url = "https://hooks.example.com/alert"
        mock_cfg.alert_webhook_timeout = 10

        mock_failures.return_value = [{"company_id": "abc", "ticker": "ACME", "consecutive_failures": 5}]
        mock_stale.return_value = []

        check_alerts()

        mock_webhook.assert_called_once()
        payload = mock_webhook.call_args.kwargs["payload"]
        assert len(payload["failure_alerts"]) == 1

    @patch("symbology.scheduler.alerts.scheduler_settings")
    @patch("symbology.scheduler.alerts.send_webhook")
    @patch("symbology.scheduler.alerts.detect_stale_runs")
    @patch("symbology.scheduler.alerts.detect_consecutive_failures")
    def test_check_alerts_no_webhook_when_url_not_set(self, mock_failures, mock_stale, mock_webhook, mock_cfg):
        mock_cfg.alert_consecutive_failure_threshold = 3
        mock_cfg.alert_stale_run_threshold_seconds = 7200
        mock_cfg.alert_webhook_url = None
        mock_cfg.alert_webhook_timeout = 10

        mock_failures.return_value = [{"company_id": "abc", "ticker": "ACME", "consecutive_failures": 5}]
        mock_stale.return_value = []

        check_alerts()

        mock_webhook.assert_not_called()
