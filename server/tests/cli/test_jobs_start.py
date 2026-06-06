"""Tests for `jobs start` scheduling options (--delay / --scheduled-at)."""
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from click.testing import CliRunner
from uuid_extensions import uuid7


def _fake_job(scheduled_at):
    from symbology.database.jobs import JobType

    return SimpleNamespace(
        id=uuid7(),
        job_type=JobType.TEST,
        params={},
        priority=2,
        status=SimpleNamespace(value="pending"),
        scheduled_at=scheduled_at,
    )


class TestJobsStartScheduling:
    """`--delay` / `--scheduled-at` compute a naive-UTC scheduled_at for create_job."""

    def _invoke(self, args):
        from symbology.cli.jobs import start_job

        captured = {}

        def fake_create_job(jt, params=None, priority=2, max_retries=3, scheduled_at=None):
            captured["scheduled_at"] = scheduled_at
            return _fake_job(scheduled_at)

        with patch("symbology.cli.jobs.init_session"), patch(
            "symbology.cli.jobs.create_job", side_effect=fake_create_job
        ):
            result = CliRunner().invoke(start_job, args)
        return result, captured

    def test_delay_sets_scheduled_at(self):
        before = datetime.now(timezone.utc).replace(tzinfo=None)
        result, captured = self._invoke(["test", "--delay", "60"])
        assert result.exit_code == 0, result.output
        sa = captured["scheduled_at"]
        assert sa is not None and sa.tzinfo is None
        offset = (sa - before).total_seconds()
        assert 55 <= offset <= 70

    def test_no_delay_leaves_scheduled_at_none(self):
        result, captured = self._invoke(["test"])
        assert result.exit_code == 0, result.output
        assert captured["scheduled_at"] is None

    def test_scheduled_at_iso_normalized_to_naive_utc(self):
        result, captured = self._invoke(["test", "--scheduled-at", "2030-01-01T00:00:00+00:00"])
        assert result.exit_code == 0, result.output
        sa = captured["scheduled_at"]
        assert sa is not None and sa.tzinfo is None
        assert sa.year == 2030 and sa.month == 1 and sa.hour == 0

    def test_delay_and_scheduled_at_are_mutually_exclusive(self):
        result, _ = self._invoke(
            ["test", "--delay", "60", "--scheduled-at", "2030-01-01T00:00:00"]
        )
        assert result.exit_code != 0
        assert "only one" in result.output.lower()
