"""Tests for `jobs retry` short-id resolution and --force."""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import click
import pytest
from click.testing import CliRunner
from uuid_extensions import uuid7


class TestShortId:
    def test_returns_last_segment(self):
        from symbology.cli.shortid import short_id

        assert short_id("06a26957-45aa-77a4-8000-155db36481c5") == "155db36481c5"

    def test_maybe_short_id_only_shortens_uuids(self):
        from symbology.cli.shortid import maybe_short_id

        assert maybe_short_id("06a26957-09c7-7ec1-8000-f6e27d858533") == "f6e27d858533"
        # Accession numbers / tickers are not UUIDs → left intact.
        assert maybe_short_id("0001065280-26-000138") == "0001065280-26-000138"
        assert maybe_short_id("NFLX") == "NFLX"


class TestJobsListRendering:
    """The list condenses UUIDs in context and the 4 timestamps into one column."""

    def test_context_shortens_uuid_params_but_not_accession(self):
        from symbology.cli.jobs import format_job_context
        from symbology.database.jobs import JobType

        embed = SimpleNamespace(job_type=JobType.EMBED_FILING,
                                params={"filing_id": "06a26957-09c7-7ec1-8000-f6e27d858533"})
        assert format_job_context(embed) == "filing_id=f6e27d858533"

        diff = SimpleNamespace(job_type=JobType.FILING_DIFF, params={
            "from": "06a26957-09c7-7ec1-8000-f6e27d858533",
            "to": "06a26956-c908-74d3-8000-4961dd3b2859", "form": "10-K"})
        assert format_job_context(diff) == "f6e27d858533 -> 4961dd3b2859, form=10-K"

        fpc = SimpleNamespace(job_type=JobType.FILING_PAGE_CONTENT,
                              params={"accession_number": "0001065280-26-000138"})
        assert format_job_context(fpc) == "accession_number=0001065280-26-000138"

        # A ticker-bearing page job (from the CLI) curates ticker/form/year.
        fpc_ticker = SimpleNamespace(job_type=JobType.FILING_PAGE_CONTENT,
                                     params={"ticker": "MSFT", "form": "10-K", "year": 2023})
        assert format_job_context(fpc_ticker) == "ticker=MSFT, form=10-K, year=2023"

    def test_context_prepends_ticker_for_filing_jobs(self):
        from symbology.cli.jobs import format_job_context
        from symbology.database.jobs import JobType

        embed = SimpleNamespace(job_type=JobType.EMBED_FILING,
                                params={"filing_id": "06a26957-09c7-7ec1-8000-f6e27d858533"})
        meta = {"06a26957-09c7-7ec1-8000-f6e27d858533": ("AAPL", "10-K"),
                "06a26956-c908-74d3-8000-4961dd3b2859": ("AAPL", "10-K")}
        assert format_job_context(embed, meta) == "ticker=AAPL, form=10-K, filing_id=f6e27d858533"

        # filing_diff already carries its form in params; meta only adds the ticker.
        diff = SimpleNamespace(job_type=JobType.FILING_DIFF, params={
            "from": "06a26957-09c7-7ec1-8000-f6e27d858533",
            "to": "06a26956-c908-74d3-8000-4961dd3b2859", "form": "10-K"})
        assert format_job_context(diff, meta) == \
            "ticker=AAPL, f6e27d858533 -> 4961dd3b2859, form=10-K"

        # No map entry (e.g. filing not found) → unchanged, no empty ticker=/form= shown.
        assert format_job_context(embed) == "filing_id=f6e27d858533"

        # filing_page_content resolves its ticker + form by accession number.
        fpc = SimpleNamespace(job_type=JobType.FILING_PAGE_CONTENT,
                              params={"accession_number": "0001065280-26-000138"})
        assert format_job_context(fpc, {"0001065280-26-000138": ("NFLX", "10-Q")}) == \
            "ticker=NFLX, form=10-Q, accession_number=0001065280-26-000138"

    def test_when_is_status_aware(self):
        from datetime import datetime, timedelta, timezone
        from symbology.cli.jobs import format_job_when
        from symbology.database.jobs import JobStatus

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        done = SimpleNamespace(status=JobStatus.COMPLETED,
                               completed_at=now - timedelta(hours=3), updated_at=now)
        assert format_job_when(done) == "done 3h ago"

        backoff = SimpleNamespace(status=JobStatus.BACKOFF, scheduled_at=now + timedelta(seconds=90))
        assert format_job_when(backoff) == "retry in 1m"

        pending = SimpleNamespace(status=JobStatus.PENDING, created_at=now - timedelta(days=2))
        assert format_job_when(pending) == "queued 2d ago"


class TestResolveId:
    """resolve_id (via resolve_job_id): full UUID passthrough; else match last segment."""

    def test_full_uuid_passes_through_without_lookup(self):
        from symbology.cli.jobs import resolve_job_id

        full = "06a26957-45aa-77a4-8000-155db36481c5"
        # No DB session needed — a valid UUID short-circuits before any lookup.
        with patch("symbology.cli.shortid.get_db_session", side_effect=AssertionError("no lookup")):
            assert resolve_job_id(full) == full

    def _session_returning(self, ids):
        session = MagicMock()
        rows = [(i,) for i in ids]
        session.query.return_value.filter.return_value.limit.return_value.all.return_value = rows
        return session

    def test_unique_last_segment_resolves(self):
        from symbology.cli.jobs import resolve_job_id

        target = uuid7()
        with patch("symbology.cli.shortid.get_db_session", return_value=self._session_returning([target])):
            assert resolve_job_id("155db36481c5") == str(target)

    def test_ambiguous_short_id_raises(self):
        from symbology.cli.jobs import resolve_job_id

        with patch("symbology.cli.shortid.get_db_session",
                   return_value=self._session_returning([uuid7(), uuid7()])):
            with pytest.raises(click.ClickException, match="Ambiguous"):
                resolve_job_id("8000")

    def test_no_match_raises(self):
        from symbology.cli.jobs import resolve_job_id

        with patch("symbology.cli.shortid.get_db_session", return_value=self._session_returning([])):
            with pytest.raises(click.ClickException, match="No job matches"):
                resolve_job_id("deadbeef")


class TestRetryForce:
    """`jobs retry --force` re-runs completed jobs and asks handlers to regenerate."""

    def _invoke(self, args):
        from symbology.cli.jobs import retry_cmd

        captured = {}

        def fake_requeue(job_id, force=False, extra_params=None):
            captured["job_id"] = job_id
            captured["force"] = force
            captured["extra_params"] = extra_params
            return SimpleNamespace(id=job_id, status=SimpleNamespace(value="pending"))

        with patch("symbology.cli.jobs.init_session"), \
             patch("symbology.cli.jobs.resolve_job_id", side_effect=lambda x: x), \
             patch("symbology.cli.jobs.requeue_job", side_effect=fake_requeue):
            result = CliRunner().invoke(retry_cmd, args)
        return result, captured

    def test_force_passes_force_and_params(self):
        result, captured = self._invoke(["155db36481c5", "--force"])
        assert result.exit_code == 0, result.output
        assert captured["force"] is True
        assert captured["extra_params"] == {"force": True}

    def test_plain_retry_does_not_force(self):
        result, captured = self._invoke(["155db36481c5"])
        assert result.exit_code == 0, result.output
        assert captured["force"] is False
        assert captured["extra_params"] is None
