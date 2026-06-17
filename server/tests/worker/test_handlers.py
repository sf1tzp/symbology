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

        embedded, diffed = [], []
        with patch.dict("sys.modules", {
            "symbology.ingestion.edgar_db": MagicMock(),
            "symbology.ingestion.edgar_db.accessors": MagicMock(),
            "symbology.ingestion.ingestion_helpers": MagicMock(ingest_filings=mock_ingest),
        }):
            with patch("symbology.utils.config.settings", mock_settings), \
                 patch("symbology.worker.handlers._enqueue_embed_filing", side_effect=embedded.append), \
                 patch("symbology.worker.handlers._enqueue_filing_diff_for", side_effect=diffed.append):
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
        # Each ingested filing gets an EMBED_FILING and a FILING_DIFF enqueued.
        assert embedded == [str(filing_id)]
        assert diffed == [str(filing_id)]

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
                 patch("symbology.worker.handlers._enqueue_embed_filing"), \
                 patch("symbology.worker.handlers._enqueue_filing_diff_for"):
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


class TestFilingIngestionInFlight:
    """The matcher that decides whether a FILING_INGESTION job is already queued."""

    def test_matches_by_ticker_and_form(self):
        from symbology.worker.handlers import _filing_ingestion_in_flight
        jobs = [SimpleNamespace(params={"ticker": "aapl", "form": "10-Q"})]
        assert _filing_ingestion_in_flight("AAPL", "10-Q", jobs) is True

    def test_defaults_missing_form_to_annual(self):
        from symbology.worker.handlers import _filing_ingestion_in_flight
        jobs = [SimpleNamespace(params={"ticker": "AAPL"})]  # no form → 10-K
        assert _filing_ingestion_in_flight("AAPL", "10-K", jobs) is True
        assert _filing_ingestion_in_flight("AAPL", "10-Q", jobs) is False

    def test_no_match_for_different_ticker_or_form(self):
        from symbology.worker.handlers import _filing_ingestion_in_flight
        jobs = [
            SimpleNamespace(params={"ticker": "MSFT", "form": "10-K"}),
            SimpleNamespace(params={"ticker": "AAPL", "form": "10-Q"}),
        ]
        assert _filing_ingestion_in_flight("AAPL", "10-K", jobs) is False

    def test_empty_active_jobs(self):
        from symbology.worker.handlers import _filing_ingestion_in_flight
        assert _filing_ingestion_in_flight("AAPL", "10-K", []) is False


class TestRequiredCompanyForms:
    def test_annual_needs_only_itself(self):
        from symbology.worker.handlers import _required_company_forms
        assert _required_company_forms("10-K") == ["10-K"]

    def test_quarterly_also_anchors_on_annual(self):
        from symbology.worker.handlers import _required_company_forms
        assert _required_company_forms("10-Q") == ["10-Q", "10-K"]


class TestAwaitFilingIngestion:
    """Queue FILING_INGESTION for missing forms, defer this job (no inline ingest)."""

    def _patches(self, active_jobs, created):
        def fake_create_job(job_type, params=None, priority=2, scheduled_at=None):
            job = SimpleNamespace(id=uuid7(), job_type=job_type, params=params,
                                  priority=priority)
            created.append(job)
            return job

        return (
            patch("symbology.database.jobs.get_active_jobs", return_value=active_jobs),
            patch("symbology.database.jobs.create_job", side_effect=fake_create_job),
        )

    def test_queues_each_missing_form_then_raises(self):
        import pytest
        from symbology.worker.handlers import _await_filing_ingestion, DependencyNotReady
        from symbology.database.jobs import JobType

        created = []
        p1, p2 = self._patches(active_jobs=[], created=created)
        with p1, p2, pytest.raises(DependencyNotReady):
            _await_filing_ingestion("GM", ["10-Q", "10-K"], lookback=5,
                                    reason_subject="company page GM 10-Q")

        assert {j.params["form"] for j in created} == {"10-Q", "10-K"}
        assert all(j.job_type == JobType.FILING_INGESTION for j in created)
        assert all(j.params["ticker"] == "GM" and j.params["include_documents"] for j in created)
        # lookback=5 bumps the 10-Q count to max(6, 6)=6 and 10-K to max(5, 6)=6.
        assert {j.params["form"]: j.params["count"] for j in created} == {"10-Q": 6, "10-K": 6}

    def test_skips_form_already_in_flight(self):
        import pytest
        from symbology.worker.handlers import _await_filing_ingestion, DependencyNotReady

        created = []
        active = [SimpleNamespace(params={"ticker": "GM", "form": "10-Q"})]
        p1, p2 = self._patches(active_jobs=active, created=created)
        with p1, p2, pytest.raises(DependencyNotReady):
            _await_filing_ingestion("GM", ["10-Q", "10-K"],
                                    reason_subject="company page GM 10-Q")

        # 10-Q already running → only the 10-K is queued.
        assert [j.params["form"] for j in created] == ["10-K"]

    def test_queues_nothing_when_all_in_flight(self):
        import pytest
        from symbology.worker.handlers import _await_filing_ingestion, DependencyNotReady

        created = []
        active = [SimpleNamespace(params={"ticker": "GM", "form": "10-K"})]
        p1, p2 = self._patches(active_jobs=active, created=created)
        with p1, p2, pytest.raises(DependencyNotReady):
            _await_filing_ingestion("GM", ["10-K"],
                                    reason_subject="filing page GM 2024 10-K")
        assert created == []


class TestCompanyPageIngestionGate:
    """handle_company_page_content defers (BACKOFF) on missing ingestion, never fails."""

    def test_uningested_company_queues_ingestion_and_backs_off(self):
        import pytest
        from symbology.worker.handlers import handle_company_page_content, DependencyNotReady
        from symbology.database.jobs import JobType

        created = []

        def fake_create_job(job_type, params=None, priority=2, scheduled_at=None):
            job = SimpleNamespace(id=uuid7(), job_type=job_type, params=params)
            created.append(job)
            return job

        with patch("symbology.database.companies.get_company_by_ticker", return_value=None), \
             patch("symbology.database.jobs.get_active_jobs", return_value=[]), \
             patch("symbology.database.jobs.create_job", side_effect=fake_create_job), \
             pytest.raises(DependencyNotReady):
            handle_company_page_content({"ticker": "GM", "form": "10-Q"})

        # A 10-Q page with no ingestion queues both the quarter and its 10-K anchor.
        assert {j.params["form"] for j in created} == {"10-Q", "10-K"}
        assert all(j.job_type == JobType.FILING_INGESTION for j in created)

    def test_quarterly_waits_on_inflight_annual_anchor(self):
        import pytest
        from symbology.worker.handlers import handle_company_page_content, DependencyNotReady

        company = SimpleNamespace(id=uuid7(), ticker="GM")
        # Primary 10-Q present, but the 10-K anchor ingestion is still running.
        annual_inflight = [SimpleNamespace(params={"ticker": "GM", "form": "10-K"})]
        with patch("symbology.database.companies.get_company_by_ticker", return_value=company), \
             patch("symbology.worker.handlers._company_has_filings", return_value=True), \
             patch("symbology.database.jobs.get_active_jobs", return_value=annual_inflight), \
             pytest.raises(DependencyNotReady):
            handle_company_page_content({"ticker": "GM", "form": "10-Q"})

    def test_proceeds_to_pipeline_when_ready(self):
        from symbology.worker.handlers import handle_company_page_content

        company = SimpleNamespace(id=uuid7(), ticker="GM")
        page = SimpleNamespace(id=uuid7())
        created = []

        def fake_create_job(job_type, params=None, priority=2, scheduled_at=None):
            created.append(SimpleNamespace(job_type=job_type, params=params, id=uuid7()))
            return created[-1]

        with patch("symbology.database.companies.get_company_by_ticker", return_value=company), \
             patch("symbology.worker.handlers._company_has_filings", return_value=True), \
             patch("symbology.database.jobs.get_active_jobs", return_value=[]), \
             patch("symbology.database.jobs.create_job", side_effect=fake_create_job), \
             patch("symbology.worker.page_pipelines.company_page_content_pipeline",
                   return_value=page) as pipeline:
            result = handle_company_page_content({"ticker": "GM", "form": "10-Q"})

        pipeline.assert_called_once()
        assert result["company_page_content_id"] == str(page.id)
        # The company page no longer enqueues any diff work — diffs are triggered at
        # ingestion (filing-domain), so nothing is created here.
        assert created == []


class TestFilingPageIngestionGate:
    """handle_company_page_content's filing-page sibling: ticker/year ingestion gate."""

    def _common(self, company, active_jobs):
        # Session whose Filing query yields no rows, so the handler's nested
        # _find_filing resolves to None (the "target year not present" branch).
        session = MagicMock()
        session.query.return_value.filter.return_value.all.return_value = []
        return (
            patch("symbology.database.companies.get_company_by_ticker", return_value=company),
            patch("symbology.database.jobs.get_active_jobs", return_value=active_jobs),
            patch("symbology.database.base.get_db_session", return_value=session),
        )

    def test_uningested_company_backs_off(self):
        import pytest
        from symbology.worker.handlers import handle_filing_page_content, DependencyNotReady

        created = []

        def fake_create_job(job_type, params=None, priority=2, scheduled_at=None):
            created.append(SimpleNamespace(job_type=job_type, params=params, id=uuid7()))
            return created[-1]

        p1, p2, p3 = self._common(company=None, active_jobs=[])
        with p1, p2, p3, \
             patch("symbology.database.jobs.create_job", side_effect=fake_create_job), \
             pytest.raises(DependencyNotReady):
            handle_filing_page_content({"ticker": "GM", "year": 2024, "form": "10-K"})
        assert [j.params["form"] for j in created] == ["10-K"]

    def test_year_absent_after_ingestion_is_hard_error(self):
        import pytest
        from symbology.worker.handlers import handle_filing_page_content

        company = SimpleNamespace(id=uuid7(), ticker="GM")
        p1, p2, p3 = self._common(company=company, active_jobs=[])
        with p1, p2, p3, \
             patch("symbology.worker.handlers._company_has_filings", return_value=True), \
             pytest.raises(ValueError):
            handle_filing_page_content({"ticker": "GM", "year": 1999, "form": "10-K"})

    def test_never_ingested_form_backs_off(self):
        import pytest
        from symbology.worker.handlers import handle_filing_page_content, DependencyNotReady

        company = SimpleNamespace(id=uuid7(), ticker="GM")
        created = []

        def fake_create_job(job_type, params=None, priority=2, scheduled_at=None):
            created.append(SimpleNamespace(job_type=job_type, params=params, id=uuid7()))
            return created[-1]

        p1, p2, p3 = self._common(company=company, active_jobs=[])
        with p1, p2, p3, \
             patch("symbology.worker.handlers._company_has_filings", return_value=False), \
             patch("symbology.database.jobs.create_job", side_effect=fake_create_job), \
             pytest.raises(DependencyNotReady):
            handle_filing_page_content({"ticker": "GM", "year": 2024, "form": "10-K"})
        assert [j.params["form"] for j in created] == ["10-K"]


class TestFilingPageNoDocumentsSkip:
    """A filing with none of the form's documents is a benign skip, not a failure."""

    def test_accession_path_skips_without_raising(self):
        from symbology.worker.handlers import handle_filing_page_content
        from symbology.worker.page_pipelines import FilingHasNoPageableDocuments

        filing = SimpleNamespace(id=uuid7())
        with patch("symbology.worker.handlers._resolve_filing_by_accession", return_value=filing), \
             patch("symbology.worker.page_pipelines.filing_page_content_pipeline",
                   side_effect=FilingHasNoPageableDocuments(filing.id)):
            result = handle_filing_page_content({"accession_number": "0001326160-26-000026"})

        # Job completes (no exception → no retry), with no page published.
        assert result["skipped"] == "no_documents"
        assert result["filing_id"] == str(filing.id)
        assert "filing_page_content_id" not in result


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

    def test_rejects_incompatible_forms(self):
        import pytest
        from symbology.worker.handlers import handle_filing_diff
        cid = uuid7()
        a = _fake_diff_filing("accA", cid, form="10-K")
        b = _fake_diff_filing("accB", cid, form="8-K")
        with patch("symbology.worker.handlers._resolve_filing_token", side_effect=[a, b]), \
             pytest.raises(ValueError):
            handle_filing_diff({"from": "accA", "to": "accB"})

    def test_allows_10k_10q_anchor_pair(self):
        """A 10-K↔10-Q pair is the cycle-anchor diff; tagged with the newer form."""
        from symbology.worker.handlers import handle_filing_diff
        cid = uuid7()
        annual = _fake_diff_filing("accK", cid, form="10-K", period_year=2023)
        quarter = _fake_diff_filing("accQ", cid, form="10-Q", period_year=2024)
        captured = {}

        def fake_pipeline(left, right, form, generate_summaries=True):
            captured["left"], captured["right"], captured["form"] = left, right, form
            return []

        with patch("symbology.worker.handlers._resolve_filing_token", side_effect=[annual, quarter]), \
             patch("symbology.worker.handlers._filing_ready_for_diff", return_value=True), \
             patch("symbology.worker.diff_pipeline.filing_diff_pipeline", side_effect=fake_pipeline):
            handle_filing_diff({"from": "accK", "to": "accQ", "generate_summaries": False})

        # Older (annual) is left, newer (quarter) is right; diff tagged quarterly.
        assert captured["left"] is annual and captured["right"] is quarter
        assert captured["form"] == "10-Q"

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
            result = handle_filing_diff({"from": "accNew", "to": "accOld",
                                         "generate_summaries": False})

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
             patch("symbology.worker.config_loader.load_pipeline_config",
                   return_value=SimpleNamespace(form_document_types={"10-K": ["risk_factors"]})), \
             patch("symbology.worker.page_pipelines._filing_has_pageable_documents", return_value=True), \
             patch("symbology.database.jobs.get_active_jobs", return_value=[]), \
             patch("symbology.database.jobs.create_job", side_effect=fake_create_job), \
             pytest.raises(DependencyNotReady):
            handle_filing_diff({"from": "accA", "to": "accB"})

        from symbology.database.jobs import JobType
        embeds = [j for j in created if j.job_type == JobType.EMBED_FILING]
        successors = [j for j in created if j.job_type == JobType.FILING_DIFF]
        assert len(embeds) == 2  # both sides not ready (but have docs) → an embed job each
        assert successors == []  # no FILING_DIFF successor copy; worker defers this job

    def test_skips_when_a_side_has_no_documents(self):
        """A not-ready side that has no documents can never embed → skip, not backoff."""
        from symbology.worker.handlers import handle_filing_diff
        cid = uuid7()
        a = _fake_diff_filing("accA", cid, period_year=2023)
        b = _fake_diff_filing("accB", cid, period_year=2024)
        created = []

        def fake_create_job(job_type, params=None, priority=2, scheduled_at=None):
            created.append(SimpleNamespace(id=uuid7(), job_type=job_type, params=params))
            return created[-1]

        with patch("symbology.worker.handlers._resolve_filing_token", side_effect=[a, b]), \
             patch("symbology.worker.handlers._filing_ready_for_diff", return_value=False), \
             patch("symbology.worker.config_loader.load_pipeline_config",
                   return_value=SimpleNamespace(form_document_types={"10-K": ["risk_factors"]})), \
             patch("symbology.worker.page_pipelines._filing_has_pageable_documents", return_value=False), \
             patch("symbology.database.jobs.get_active_jobs", return_value=[]), \
             patch("symbology.database.jobs.create_job", side_effect=fake_create_job):
            result = handle_filing_diff({"from": "accA", "to": "accB"})

        assert result["skipped"] == "no_documents"
        assert created == []  # no EMBED enqueued, no backoff


def _fake_section_diff(kind="reworded", summarized=False, ops=None):
    return SimpleNamespace(id=uuid7(), change_kind=kind, ops=ops or [],
                           summary_content_id=uuid7() if summarized else None)


def _fake_diff_set(sds):
    return SimpleNamespace(id=uuid7(), section_diffs=sds,
                           document_type=SimpleNamespace(value="risk_factors"))


class TestFilingDiffEnqueuesSummaries:
    """FILING_DIFF computes structural diff only, then enqueues DIFF_SUMMARY jobs."""

    def _run(self, diff_sets, active=None, generate_summaries=True):
        from symbology.worker.handlers import handle_filing_diff
        cid = uuid7()
        newer = _fake_diff_filing("accNew", cid, period_year=2024)
        older = _fake_diff_filing("accOld", cid, period_year=2023)
        created = []

        def fake_pipeline(left, right, form, generate_summaries=False):
            # Structural-only: the handler must NOT ask the pipeline to summarise.
            assert generate_summaries is False
            return diff_sets

        def fake_create_job(job_type, params=None, priority=2, scheduled_at=None):
            created.append(SimpleNamespace(id=uuid7(), job_type=job_type, params=params,
                                           priority=priority))
            return created[-1]

        with patch("symbology.worker.handlers._resolve_filing_token", side_effect=[newer, older]), \
             patch("symbology.worker.handlers._filing_ready_for_diff", return_value=True), \
             patch("symbology.worker.diff_pipeline.filing_diff_pipeline", side_effect=fake_pipeline), \
             patch("symbology.database.jobs.get_active_jobs", return_value=active or []), \
             patch("symbology.database.jobs.create_job", side_effect=fake_create_job):
            result = handle_filing_diff({"from": "accNew", "to": "accOld",
                                         "generate_summaries": generate_summaries})
        return result, created

    def test_enqueues_one_job_per_set_with_displayed_changes(self):
        from symbology.database.jobs import JobType
        ds1 = _fake_diff_set([_fake_section_diff("escalated")])
        ds2 = _fake_diff_set([_fake_section_diff("reworded")])
        result, created = self._run([ds1, ds2])
        summary_jobs = [j for j in created if j.job_type == JobType.DIFF_SUMMARY]
        assert {j.params["diff_set_id"] for j in summary_jobs} == {str(ds1.id), str(ds2.id)}
        assert all(j.priority == 5 for j in summary_jobs)
        assert result["summary_jobs_enqueued"] == 2

    def test_skips_sets_with_no_displayed_unsummarised_changes(self):
        from symbology.database.jobs import JobType
        # Not-displayed kinds (new/removed/unchanged) and already-summarised rows
        # don't warrant a job — they never appear as cards / list items.
        ds1 = _fake_diff_set([_fake_section_diff("new"), _fake_section_diff("unchanged")])
        ds2 = _fake_diff_set([_fake_section_diff("reworded", summarized=True)])
        _, created = self._run([ds1, ds2])
        assert [j for j in created if j.job_type == JobType.DIFF_SUMMARY] == []

    def test_skips_when_summary_already_in_flight(self):
        from symbology.database.jobs import JobType
        ds = _fake_diff_set([_fake_section_diff("escalated")])
        active = [SimpleNamespace(params={"diff_set_id": str(ds.id)})]
        _, created = self._run([ds], active=active)
        assert [j for j in created if j.job_type == JobType.DIFF_SUMMARY] == []

    def test_no_jobs_when_summaries_disabled(self):
        from symbology.database.jobs import JobType
        ds = _fake_diff_set([_fake_section_diff("escalated")])
        _, created = self._run([ds], generate_summaries=False)
        assert [j for j in created if j.job_type == JobType.DIFF_SUMMARY] == []


class TestHandleDiffSummary:
    """DIFF_SUMMARY summarises one diff set's top changed topics."""

    def test_requires_diff_set_id(self):
        import pytest
        from symbology.worker.handlers import handle_diff_summary
        with pytest.raises(ValueError):
            handle_diff_summary({})

    def test_noop_when_diff_set_gone(self):
        from symbology.worker.handlers import handle_diff_summary
        session = MagicMock()
        session.query.return_value.filter.return_value.first.return_value = None
        with patch("symbology.database.base.get_db_session", return_value=session):
            result = handle_diff_summary({"diff_set_id": str(uuid7())})
        assert result["summarized"] == 0 and result["skipped"] == "set_gone"

    def test_summarises_the_set(self):
        from symbology.worker.handlers import handle_diff_summary
        diff_set = SimpleNamespace(id=uuid7(), company_id=uuid7(), form="10-K")
        company = SimpleNamespace(id=diff_set.company_id)
        session = MagicMock()
        session.query.return_value.filter.return_value.first.return_value = diff_set
        with patch("symbology.database.base.get_db_session", return_value=session), \
             patch("symbology.database.companies.get_company", return_value=company), \
             patch("symbology.worker.diff_pipeline.summarize_diff_set", return_value=7) as summ:
            result = handle_diff_summary({"diff_set_id": str(diff_set.id), "max_summaries": 7})
        summ.assert_called_once()
        assert summ.call_args.kwargs["max_summaries"] == 7
        assert result["summarized"] == 7


class TestPreviousPeriodicFiling:
    def _session(self, candidates):
        session = MagicMock()
        session.query.return_value.filter.return_value.all.return_value = candidates
        return session

    def test_picks_most_recent_earlier_filing(self):
        from symbology.worker.handlers import _previous_periodic_filing

        cid = uuid7()
        this = _fake_diff_filing("d", cid, period_year=2024)
        older = _fake_diff_filing("c", cid, period_year=2023)
        oldest = _fake_diff_filing("b", cid, period_year=2022)
        session = self._session([oldest, older])  # query excludes `this`
        prev = _previous_periodic_filing(session, this)
        assert prev is older

    def test_none_when_earliest(self):
        from symbology.worker.handlers import _previous_periodic_filing

        cid = uuid7()
        this = _fake_diff_filing("a", cid, period_year=2020)
        session = self._session([])  # no other same-form filings
        assert _previous_periodic_filing(session, this) is None

    def test_quarter_anchors_on_prior_annual(self):
        """A 10-Q's first-of-cycle predecessor is the anchoring 10-K."""
        from datetime import date
        from symbology.worker.handlers import _previous_periodic_filing

        cid = uuid7()
        q1 = _fake_diff_filing("q1", cid, form="10-Q")
        q1.period_of_report = date(2024, 3, 31)
        annual = _fake_diff_filing("k23", cid, form="10-K")
        annual.period_of_report = date(2023, 12, 31)
        session = self._session([annual])  # only the prior 10-K exists
        prev = _previous_periodic_filing(session, q1)
        assert prev is annual


class TestEnqueueFilingDiffFor:
    """Ingestion enqueues a FILING_DIFF of a filing vs its previous periodic filing."""

    def _patches(self, filing, prev, has_diff, active_jobs, created):
        cfg = SimpleNamespace(form_document_types={"10-K": ["risk_factors"]})
        session = MagicMock()
        # The function loads the filing by id before resolving its predecessor.
        session.query.return_value.filter.return_value.first.return_value = filing

        def fake_create_job(job_type, params=None, priority=2, scheduled_at=None):
            created.append(SimpleNamespace(job_type=job_type, params=params, id=uuid7()))
            return created[-1]

        return (
            patch("symbology.database.base.get_db_session", return_value=session),
            patch("symbology.worker.handlers._previous_periodic_filing", return_value=prev),
            patch("symbology.worker.config_loader.load_pipeline_config", return_value=cfg),
            patch("symbology.worker.handlers._pair_has_current_diff", return_value=has_diff),
            patch("symbology.worker.page_pipelines._filing_has_pageable_documents", return_value=True),
            patch("symbology.database.jobs.get_active_jobs", return_value=active_jobs),
            patch("symbology.database.jobs.create_job", side_effect=fake_create_job),
        )

    def test_enqueues_pairwise_diff(self):
        from symbology.worker.handlers import _enqueue_filing_diff_for
        from symbology.database.jobs import JobType

        cid = uuid7()
        prev = _fake_diff_filing("prev", cid, period_year=2023)
        filing = _fake_diff_filing("cur", cid, period_year=2024)
        created = []
        ps = self._patches(filing=filing, prev=prev, has_diff=False, active_jobs=[], created=created)
        with ps[0], ps[1], ps[2], ps[3], ps[4], ps[5], ps[6]:
            _enqueue_filing_diff_for(str(filing.id))

        assert [j.job_type for j in created] == [JobType.FILING_DIFF]
        assert created[0].params == {
            "left_filing_id": str(prev.id),
            "right_filing_id": str(filing.id),
            "form": "10-K",
        }

    def test_skips_when_no_prior_filing(self):
        from symbology.worker.handlers import _enqueue_filing_diff_for

        filing = _fake_diff_filing("cur", uuid7(), period_year=2024)
        created = []
        ps = self._patches(filing=filing, prev=None, has_diff=False, active_jobs=[], created=created)
        with ps[0], ps[1], ps[2], ps[3], ps[4], ps[5], ps[6]:
            _enqueue_filing_diff_for(str(filing.id))
        assert created == []

    def test_skips_when_pair_already_diffed(self):
        from symbology.worker.handlers import _enqueue_filing_diff_for

        cid = uuid7()
        prev = _fake_diff_filing("prev", cid, period_year=2023)
        filing = _fake_diff_filing("cur", cid, period_year=2024)
        created = []
        ps = self._patches(filing=filing, prev=prev, has_diff=True, active_jobs=[], created=created)
        with ps[0], ps[1], ps[2], ps[3], ps[4], ps[5], ps[6]:
            _enqueue_filing_diff_for(str(filing.id))
        assert created == []

    def test_skips_when_diff_in_flight(self):
        from symbology.worker.handlers import _enqueue_filing_diff_for

        cid = uuid7()
        prev = _fake_diff_filing("prev", cid, period_year=2023)
        filing = _fake_diff_filing("cur", cid, period_year=2024)
        created = []
        active = [SimpleNamespace(params={"left_filing_id": str(prev.id),
                                          "right_filing_id": str(filing.id)})]
        ps = self._patches(filing=filing, prev=prev, has_diff=False, active_jobs=active, created=created)
        with ps[0], ps[1], ps[2], ps[3], ps[4], ps[5], ps[6]:
            _enqueue_filing_diff_for(str(filing.id))
        assert created == []


class TestPublishedL1SummaryHashes:
    """The doc-level dependency gate in the company-page change-report path.

    A filing may carry a published *filing* page (passing the coarse gate in
    company_page_content_pipeline) yet still lack an individual document's page
    summary. That must surface as a dependency (FilingPageContentNotReady), not
    a terminal PageContentGenerationError — otherwise the company page
    dead-letters instead of backing off until the filing page is regenerated.
    """

    def test_missing_doc_page_summary_raises_not_ready_with_filing_id(self):
        import pytest
        from symbology.worker import page_pipelines as pp

        filing = SimpleNamespace(id=uuid7(), documents=[])
        document = SimpleNamespace(id=uuid7(), content_hash="abc123")

        with patch.object(pp, "select_substantive_document", return_value=document), \
             patch.object(pp, "get_current_document_page_content", return_value=None), \
             pytest.raises(pp.FilingPageContentNotReady) as ei:
            pp._published_l1_summary_hashes([filing], "market_risk")

        # Carries the offending filing id so _await_filing_page_content can
        # re-queue its filing page and the company page backs off (not fails).
        assert ei.value.missing_filing_ids == [str(filing.id)]

    def test_absent_section_is_skipped_not_a_dependency(self):
        from symbology.worker import page_pipelines as pp

        filing = SimpleNamespace(id=uuid7(), documents=[])
        # select_substantive_document returns None → section genuinely absent.
        with patch.object(pp, "select_substantive_document", return_value=None), \
             patch.object(pp, "get_current_document_page_content", return_value=None):
            assert pp._published_l1_summary_hashes([filing], "market_risk") == []
