"""Tests for job handlers with mocked DB/LLM/EDGAR dependencies."""
from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from uuid_extensions import uuid7

from symbology.worker.handlers import (
    handle_test,
)


class TestHandleTest:
    def test_echoes_params(self):
        result = handle_test({"foo": "bar"})
        assert result == {"echo": {"foo": "bar"}, "status": "ok"}

    def test_empty_params(self):
        result = handle_test({})
        assert result["status"] == "ok"


class TestHandleCompanyIngestion:
    def test_ingests_company(self):
        company_id = uuid7()
        mock_edgar_company = MagicMock()
        mock_edgar_company.name = "Apple Inc."

        mock_edgar_login = MagicMock()
        mock_ingest = MagicMock(return_value=(mock_edgar_company, company_id))
        mock_settings = MagicMock()
        mock_settings.edgar_api.edgar_contact = "test@test.com"

        with patch.dict("sys.modules", {
            "symbology.ingestion.edgar_db": MagicMock(),
            "symbology.ingestion.edgar_db.accessors": MagicMock(edgar_login=mock_edgar_login),
            "symbology.ingestion.ingestion_helpers": MagicMock(ingest_company=mock_ingest),
        }):
            from symbology.worker.handlers import handle_company_ingestion
            with patch("symbology.utils.config.settings", mock_settings):
                result = handle_company_ingestion({"ticker": "AAPL"})
        assert result["ticker"] == "AAPL"
        assert result["company_id"] == str(company_id)
        assert result["name"] == "Apple Inc."

    def test_raises_on_missing_ticker(self):
        """Missing ticker key should raise KeyError."""
        from symbology.worker.handlers import handle_company_ingestion
        try:
            # Patch the lazy imports so they don't fail, but the KeyError on params should hit first
            with patch.dict("sys.modules", {
                "symbology.ingestion.edgar_db": MagicMock(),
                "symbology.ingestion.edgar_db.accessors": MagicMock(),
                "symbology.ingestion.ingestion_helpers": MagicMock(),
            }):
                handle_company_ingestion({})
                assert False, "Should have raised KeyError"
        except KeyError:
            pass


class TestHandleFilingIngestion:
    def test_ingests_filings(self):
        filing_id = uuid7()
        mock_ingest = MagicMock(return_value=[("AAPL", "10-K", "2023-09-30", filing_id)])
        mock_settings = MagicMock()
        mock_settings.edgar_api.edgar_contact = "test@test.com"

        embedded = []
        with patch.dict("sys.modules", {
            "symbology.ingestion.edgar_db": MagicMock(),
            "symbology.ingestion.edgar_db.accessors": MagicMock(),
            "symbology.ingestion.ingestion_helpers": MagicMock(ingest_filings=mock_ingest),
        }):
            with patch("symbology.utils.config.settings", mock_settings), \
                 patch("symbology.worker.handlers._enqueue_embed_filing", side_effect=embedded.append):
                from symbology.worker.handlers import handle_filing_ingestion
                result = handle_filing_ingestion({
                    "company_id": str(uuid7()),
                    "ticker": "AAPL",
                    "form": "10-K",
                    "count": 1,
                })
        assert result["ticker"] == "AAPL"
        assert result["form"] == "10-K"
        assert len(result["filing_ids"]) == 1
        assert result["filing_ids"][0] == str(filing_id)
        # Each ingested filing gets an EMBED_FILING job enqueued.
        assert embedded == [str(filing_id)]

    def test_defaults(self):
        mock_ingest = MagicMock(return_value=[])
        mock_settings = MagicMock()
        mock_settings.edgar_api.edgar_contact = "test@test.com"

        with patch.dict("sys.modules", {
            "symbology.ingestion.edgar_db": MagicMock(),
            "symbology.ingestion.edgar_db.accessors": MagicMock(),
            "symbology.ingestion.ingestion_helpers": MagicMock(ingest_filings=mock_ingest),
        }):
            with patch("symbology.utils.config.settings", mock_settings):
                from symbology.worker.handlers import handle_filing_ingestion
                result = handle_filing_ingestion({
                    "company_id": str(uuid7()),
                    "ticker": "MSFT",
                })
        assert result["form"] == "10-K"
        call_args = mock_ingest.call_args
        assert call_args[0][3] == 5  # count default
        assert call_args[0][4] is True  # include_documents default

    def test_resolves_company_from_ticker_when_company_id_absent(self):
        cid = uuid7()
        mock_ingest = MagicMock(return_value=[("AAPL", "10-K", "2023-09-30", uuid7())])
        mock_settings = MagicMock()
        mock_settings.edgar_api.edgar_contact = "test@test.com"

        with patch.dict("sys.modules", {
            "symbology.ingestion.edgar_db": MagicMock(),
            "symbology.ingestion.edgar_db.accessors": MagicMock(),
            "symbology.ingestion.ingestion_helpers": MagicMock(ingest_filings=mock_ingest),
        }):
            with patch("symbology.utils.config.settings", mock_settings), \
                 patch(
                     "symbology.database.companies.get_company_by_ticker",
                     return_value=SimpleNamespace(id=cid),
                 ), \
                 patch("symbology.worker.handlers._enqueue_embed_filing"):
                from symbology.worker.handlers import handle_filing_ingestion
                result = handle_filing_ingestion({"ticker": "AAPL", "count": 1})

        # No company_id passed → resolved from ticker and threaded into ingest_filings.
        assert mock_ingest.call_args[0][0] == cid
        assert result["ticker"] == "AAPL"


def _fake_filing(accession, ticker, form="10-K", period_year=2024, filed_year=2024):
    return SimpleNamespace(
        id=uuid7(),
        accession_number=accession,
        form=form,
        company=SimpleNamespace(ticker=ticker),
        period_of_report=date(period_year, 12, 31) if period_year else None,
        filing_date=date(filed_year, 2, 1) if filed_year else None,
    )


class TestFilingPageJobInFlight:
    """The matcher that decides whether a filing's page job is already queued."""

    def test_matches_by_accession_number(self):
        from symbology.worker.handlers import _filing_page_job_in_flight
        filing = _fake_filing("0000320193-24-000123", "AAPL")
        jobs = [SimpleNamespace(params={"accession_number": "0000320193-24-000123"})]
        assert _filing_page_job_in_flight(filing, jobs) is True

    def test_matches_by_ticker_year_form(self):
        from symbology.worker.handlers import _filing_page_job_in_flight
        filing = _fake_filing("acc-1", "AAPL", period_year=2024)
        jobs = [SimpleNamespace(params={"ticker": "aapl", "year": "2024", "form": "10-K"})]
        assert _filing_page_job_in_flight(filing, jobs) is True

    def test_matches_year_against_filing_date_when_period_differs(self):
        from symbology.worker.handlers import _filing_page_job_in_flight
        # Job targets the filing-date year (2025), period_of_report is 2024.
        filing = _fake_filing("acc-1", "AAPL", period_year=2024, filed_year=2025)
        jobs = [SimpleNamespace(params={"ticker": "AAPL", "year": 2025})]
        assert _filing_page_job_in_flight(filing, jobs) is True

    def test_no_match_for_different_filing(self):
        from symbology.worker.handlers import _filing_page_job_in_flight
        filing = _fake_filing("acc-1", "AAPL", period_year=2024)
        jobs = [
            SimpleNamespace(params={"accession_number": "other-acc"}),
            SimpleNamespace(params={"ticker": "MSFT", "year": 2024}),
            SimpleNamespace(params={"ticker": "AAPL", "year": 2020}),
        ]
        assert _filing_page_job_in_flight(filing, jobs) is False

    def test_empty_active_jobs(self):
        from symbology.worker.handlers import _filing_page_job_in_flight
        assert _filing_page_job_in_flight(_fake_filing("a", "AAPL"), []) is False


class TestAwaitFilingPageContent:
    """The dependency-recovery path: queue missing filing jobs, defer the company job."""

    def _patches(self, filings_by_id, active_jobs, created):
        """Patch the local imports inside _await_filing_page_content."""
        session = MagicMock()

        def query(_model):
            q = MagicMock()
            def filter_(expr):
                fq = MagicMock()
                # The handler builds Filing.id == UUID(fid); resolve via call order.
                fq.first.side_effect = lambda: filings_by_id.pop(0) if filings_by_id else None
                return fq
            q.filter.side_effect = filter_
            return q
        session.query.side_effect = query

        def fake_create_job(job_type, params=None, priority=2, scheduled_at=None):
            job = SimpleNamespace(id=uuid7(), job_type=job_type, params=params,
                                  scheduled_at=scheduled_at)
            created.append(job)
            return job

        return (
            patch("symbology.database.base.get_db_session", return_value=session),
            patch("symbology.database.jobs.get_active_jobs", return_value=active_jobs),
            patch("symbology.database.jobs.create_job", side_effect=fake_create_job),
        )

    def test_queues_filing_job_then_raises_dependency_not_ready(self):
        import pytest
        from symbology.worker.handlers import _await_filing_page_content, DependencyNotReady
        from symbology.worker.page_pipelines import FilingPageContentNotReady
        from symbology.database.jobs import JobType

        filing = _fake_filing("acc-X", "AAPL")
        exc = FilingPageContentNotReady("missing", [str(filing.id)])
        created = []
        p1, p2, p3 = self._patches([filing], active_jobs=[], created=created)
        with p1, p2, p3, pytest.raises(DependencyNotReady):
            _await_filing_page_content("AAPL", "10-K", exc)

        # The missing filing page is enqueued; crucially, NO company-page successor
        # copy is spawned — the worker defers this same job (BACKOFF) instead.
        filing_jobs = [j for j in created if j.job_type == JobType.FILING_PAGE_CONTENT]
        company_jobs = [j for j in created if j.job_type == JobType.COMPANY_PAGE_CONTENT]
        assert len(filing_jobs) == 1
        assert filing_jobs[0].params == {"accession_number": "acc-X"}
        assert company_jobs == []

    def test_waits_without_requeuing_filing_when_in_flight(self):
        import pytest
        from symbology.worker.handlers import _await_filing_page_content, DependencyNotReady
        from symbology.worker.page_pipelines import FilingPageContentNotReady

        filing = _fake_filing("acc-Y", "AAPL")
        exc = FilingPageContentNotReady("missing", [str(filing.id)])
        active = [SimpleNamespace(params={"accession_number": "acc-Y"})]
        created = []
        p1, p2, p3 = self._patches([filing], active_jobs=active, created=created)
        with p1, p2, p3, pytest.raises(DependencyNotReady):
            _await_filing_page_content("AAPL", "10-K", exc)

        # Already in flight → nothing new is enqueued (no filing job, no successor).
        assert created == []


def _fake_diff_filing(accession, company_id, form="10-K", period_year=2024, filed_year=2024):
    """A filing fake carrying the fields the embed/diff handlers read."""
    return SimpleNamespace(
        id=uuid7(),
        accession_number=accession,
        company_id=company_id,
        form=form,
        company=SimpleNamespace(ticker="AAPL", id=company_id),
        period_of_report=date(period_year, 12, 31) if period_year else None,
        filing_date=date(filed_year, 2, 1) if filed_year else None,
        documents=[],
    )


class TestHandleEmbedFiling:
    """EMBED_FILING loops chunk/embed/cluster over a filing's documents."""

    def test_processes_each_document(self):
        from symbology.worker.handlers import handle_embed_filing

        cid = uuid7()
        filing = _fake_diff_filing("acc-1", cid)
        filing.documents = [SimpleNamespace(id=uuid7()), SimpleNamespace(id=uuid7())]
        calls = []
        with patch("symbology.worker.handlers._resolve_filing_token", return_value=filing), \
             patch(
                 "symbology.llm.content_processing.chunk_embed_and_cluster_document",
                 side_effect=lambda doc_id, **kw: calls.append(doc_id),
             ):
            result = handle_embed_filing({"filing_id": str(filing.id)})

        assert len(calls) == 2
        assert result["documents_processed"] == 2
        assert result["documents_total"] == 2

    def test_requires_an_identifier(self):
        import pytest
        from symbology.worker.handlers import handle_embed_filing
        with pytest.raises(ValueError):
            handle_embed_filing({})

    def test_one_document_failure_is_non_fatal(self):
        from symbology.worker.handlers import handle_embed_filing

        cid = uuid7()
        filing = _fake_diff_filing("acc-1", cid)
        filing.documents = [SimpleNamespace(id=uuid7()), SimpleNamespace(id=uuid7())]

        def flaky(doc_id, **kw):
            if doc_id == filing.documents[0].id:
                raise RuntimeError("embed server down")

        with patch("symbology.worker.handlers._resolve_filing_token", return_value=filing), \
             patch("symbology.llm.content_processing.chunk_embed_and_cluster_document", side_effect=flaky):
            result = handle_embed_filing({"filing_id": str(filing.id)})

        assert result["documents_processed"] == 1
        assert result["documents_total"] == 2


class TestOrderFilings:
    def test_returns_older_then_newer(self):
        from symbology.worker.handlers import _order_filings
        older = _fake_diff_filing("a", uuid7(), period_year=2023)
        newer = _fake_diff_filing("b", uuid7(), period_year=2024)
        assert _order_filings(newer, older) == (older, newer)
        assert _order_filings(older, newer) == (older, newer)


class TestFilingDiffInFlight:
    def test_matches_by_filing_ids(self):
        from symbology.worker.handlers import _filing_diff_in_flight
        cid = uuid7()
        left = _fake_diff_filing("accL", cid)
        right = _fake_diff_filing("accR", cid)
        jobs = [SimpleNamespace(params={"left_filing_id": str(left.id),
                                        "right_filing_id": str(right.id)})]
        assert _filing_diff_in_flight(left, right, jobs) is True

    def test_matches_by_accession_aliases(self):
        from symbology.worker.handlers import _filing_diff_in_flight
        cid = uuid7()
        left = _fake_diff_filing("accL", cid)
        right = _fake_diff_filing("accR", cid)
        jobs = [SimpleNamespace(params={"from": "accL", "to": "accR"})]
        assert _filing_diff_in_flight(left, right, jobs) is True

    def test_no_match(self):
        from symbology.worker.handlers import _filing_diff_in_flight
        cid = uuid7()
        left = _fake_diff_filing("accL", cid)
        right = _fake_diff_filing("accR", cid)
        jobs = [SimpleNamespace(params={"from": "accL", "to": "other"})]
        assert _filing_diff_in_flight(left, right, jobs) is False


class TestHandleFilingDiff:
    """FILING_DIFF validates + orders the pair, gates on embeddings, then diffs."""

    def test_rejects_same_filing(self):
        import pytest
        from symbology.worker.handlers import handle_filing_diff
        f = _fake_diff_filing("acc", uuid7())
        with patch("symbology.worker.handlers._resolve_filing_token", return_value=f), \
             pytest.raises(ValueError):
            handle_filing_diff({"from": "acc", "to": "acc"})

    def test_rejects_cross_company(self):
        import pytest
        from symbology.worker.handlers import handle_filing_diff
        a = _fake_diff_filing("accA", uuid7())
        b = _fake_diff_filing("accB", uuid7())
        with patch("symbology.worker.handlers._resolve_filing_token", side_effect=[a, b]), \
             pytest.raises(ValueError):
            handle_filing_diff({"from": "accA", "to": "accB"})

    def test_rejects_form_mismatch(self):
        import pytest
        from symbology.worker.handlers import handle_filing_diff
        cid = uuid7()
        a = _fake_diff_filing("accA", cid, form="10-K")
        b = _fake_diff_filing("accB", cid, form="10-Q")
        with patch("symbology.worker.handlers._resolve_filing_token", side_effect=[a, b]), \
             pytest.raises(ValueError):
            handle_filing_diff({"from": "accA", "to": "accB"})

    def test_runs_pipeline_when_ready_in_order(self):
        from symbology.worker.handlers import handle_filing_diff
        cid = uuid7()
        newer = _fake_diff_filing("accNew", cid, period_year=2024)
        older = _fake_diff_filing("accOld", cid, period_year=2023)
        captured = {}

        def fake_pipeline(left, right, form, generate_summaries=True):
            captured["left"], captured["right"], captured["form"] = left, right, form
            return [SimpleNamespace(document_type=SimpleNamespace(value="risk_factors"))]

        # `from`=newer, `to`=older — handler must reorder to (older, newer).
        with patch("symbology.worker.handlers._resolve_filing_token", side_effect=[newer, older]), \
             patch("symbology.worker.handlers._filing_ready_for_diff", return_value=True), \
             patch("symbology.worker.diff_pipeline.filing_diff_pipeline", side_effect=fake_pipeline):
            result = handle_filing_diff({"from": "accNew", "to": "accOld"})

        assert captured["left"] is older and captured["right"] is newer
        assert result["diff_sets"] == 1
        assert result["document_types"] == ["risk_factors"]

    def test_defers_when_not_embedded(self):
        import pytest
        from symbology.worker.handlers import handle_filing_diff, DependencyNotReady
        cid = uuid7()
        a = _fake_diff_filing("accA", cid, period_year=2023)
        b = _fake_diff_filing("accB", cid, period_year=2024)
        created = []

        def fake_create_job(job_type, params=None, priority=2, scheduled_at=None):
            job = SimpleNamespace(id=uuid7(), job_type=job_type, params=params,
                                  scheduled_at=scheduled_at)
            created.append(job)
            return job

        with patch("symbology.worker.handlers._resolve_filing_token", side_effect=[a, b]), \
             patch("symbology.worker.handlers._filing_ready_for_diff", return_value=False), \
             patch("symbology.database.jobs.get_active_jobs", return_value=[]), \
             patch("symbology.database.jobs.create_job", side_effect=fake_create_job), \
             pytest.raises(DependencyNotReady):
            handle_filing_diff({"from": "accA", "to": "accB"})

        from symbology.database.jobs import JobType
        embeds = [j for j in created if j.job_type == JobType.EMBED_FILING]
        successors = [j for j in created if j.job_type == JobType.FILING_DIFF]
        assert len(embeds) == 2  # both sides not ready → an embed job each
        assert successors == []  # no FILING_DIFF successor copy; worker defers this job


class TestHandleCompanyDiffEnsure:
    """COMPANY_DIFF now walks consecutive pairs and enqueues FILING_DIFF jobs."""

    def _run(self, filings, current_diff_for=None, active=None, created=None, extra_params=None):
        created = created if created is not None else []
        cid = uuid7()
        company = SimpleNamespace(id=cid, ticker="AAPL")
        session = MagicMock()
        session.query.return_value.filter.return_value.order_by.return_value.all.return_value = filings

        cfg = SimpleNamespace(form_document_types={"10-K": ["risk_factors"]})

        def fake_get_current(company_id, dt, right_filing_id=None):
            return (current_diff_for or {}).get(right_filing_id)

        def fake_create_job(job_type, params=None, priority=2, scheduled_at=None):
            job = SimpleNamespace(id=uuid7(), job_type=job_type, params=params)
            created.append(job)
            return job

        from symbology.worker.handlers import handle_company_diff
        params = {"ticker": "AAPL", "form": "10-K", **(extra_params or {})}
        with patch("symbology.database.companies.get_company_by_ticker", return_value=company), \
             patch("symbology.database.base.get_db_session", return_value=session), \
             patch("symbology.worker.config_loader.load_pipeline_config", return_value=cfg), \
             patch("symbology.database.section_diffs.get_current_diff_set", side_effect=fake_get_current), \
             patch("symbology.database.jobs.get_active_jobs", return_value=active or []), \
             patch("symbology.database.jobs.create_job", side_effect=fake_create_job):
            result = handle_company_diff(params)
        return result, created, company

    def test_enqueues_each_consecutive_pair(self):
        cid = uuid7()
        filings = [
            _fake_diff_filing("a", cid, period_year=2022),
            _fake_diff_filing("b", cid, period_year=2023),
            _fake_diff_filing("c", cid, period_year=2024),
        ]
        result, created, _ = self._run(filings)
        from symbology.database.jobs import JobType
        diff_jobs = [j for j in created if j.job_type == JobType.FILING_DIFF]
        assert result["pairs"] == 2
        assert result["enqueued"] == 2
        assert len(diff_jobs) == 2

    def test_skips_pair_with_existing_diff(self):
        cid = uuid7()
        f0 = _fake_diff_filing("a", cid, period_year=2023)
        f1 = _fake_diff_filing("b", cid, period_year=2024)
        # A current diff already exists for the (f0 -> f1) pair.
        existing = SimpleNamespace(left_filing_id=f0.id)
        result, created, _ = self._run([f0, f1], current_diff_for={f1.id: existing})
        assert result["enqueued"] == 0
        assert result["skipped"] == 1

    def test_single_filing_no_op(self):
        cid = uuid7()
        result, created, _ = self._run([_fake_diff_filing("a", cid)])
        assert result["pairs"] == 0 and result["enqueued"] == 0

    def test_lookback_spans_only_the_most_recent_filings(self):
        # With 4 filings but lookback=2, only the latest two (one pair) are diffed.
        cid = uuid7()
        filings = [
            _fake_diff_filing("a", cid, period_year=2021),
            _fake_diff_filing("b", cid, period_year=2022),
            _fake_diff_filing("c", cid, period_year=2023),
            _fake_diff_filing("d", cid, period_year=2024),
        ]
        result, created, _ = self._run(filings, extra_params={"lookback": 2})
        from symbology.database.jobs import JobType
        diff_jobs = [j for j in created if j.job_type == JobType.FILING_DIFF]
        assert result["pairs"] == 1
        assert result["enqueued"] == 1
        # The single pair is the most recent one (2023 -> 2024).
        assert diff_jobs[0].params["right_filing_id"] == str(filings[-1].id)
        assert diff_jobs[0].params["left_filing_id"] == str(filings[-2].id)

    def test_defers_when_company_not_ingested_yet(self):
        """Lost the race against ingestion → BACKOFF (DependencyNotReady), not a crash."""
        import pytest
        from symbology.worker.handlers import handle_company_diff, DependencyNotReady

        with patch("symbology.database.companies.get_company_by_ticker", return_value=None), \
             pytest.raises(DependencyNotReady):
            handle_company_diff({"ticker": "NVDA", "form": "10-K"})
