"""Tests for scheduler configuration."""
from symbology.scheduler.config import SchedulerSettings


class TestSchedulerSettings:
    def test_defaults(self):
        s = SchedulerSettings()
        assert s.poll_interval == 21600
        assert s.enabled_forms == ["10-K", "10-Q"]
        assert s.filing_lookback_days == 30

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("SCHEDULER_POLL_INTERVAL", "3600")
        monkeypatch.setenv("SCHEDULER_FILING_LOOKBACK_DAYS", "7")
        s = SchedulerSettings()
        assert s.poll_interval == 3600
        assert s.filing_lookback_days == 7

    def test_enabled_forms_from_env(self, monkeypatch):
        monkeypatch.setenv("SCHEDULER_ENABLED_FORMS", '["10-K"]')
        s = SchedulerSettings()
        assert s.enabled_forms == ["10-K"]
