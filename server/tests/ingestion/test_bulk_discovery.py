"""Tests for bulk discovery CSV loader functions."""
import csv
import tempfile
from pathlib import Path

from symbology.ingestion.bulk_discovery import get_sp500_ciks, load_ciks_from_csv


class TestLoadCiksFromCsv:

    def test_loads_ciks_from_csv(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("Ticker,Company,Cik\nAAPL,Apple,320193\nMSFT,Microsoft,789019\n")
        result = load_ciks_from_csv(csv_file)
        assert result == {"320193", "789019"}

    def test_normalizes_leading_zeros(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("Ticker,Company,Cik\nAAPL,Apple,0320193\nMSFT,Microsoft,0000789019\n")
        result = load_ciks_from_csv(csv_file)
        assert "320193" in result
        assert "789019" in result
        # No zero-padded versions
        assert "0320193" not in result

    def test_handles_lowercase_cik_header(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("ticker,company,cik\nAAPL,Apple,320193\n")
        result = load_ciks_from_csv(csv_file)
        assert result == {"320193"}

    def test_handles_uppercase_cik_header(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("Ticker,Company,CIK\nAAPL,Apple,320193\n")
        result = load_ciks_from_csv(csv_file)
        assert result == {"320193"}

    def test_empty_csv_returns_empty_set(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("Ticker,Company,Cik\n")
        result = load_ciks_from_csv(csv_file)
        assert result == set()


class TestGetSp500Ciks:

    def test_loads_bundled_file(self):
        ciks = get_sp500_ciks()
        assert len(ciks) >= 7
        # Spot-check known CIKs
        assert "320193" in ciks   # Apple
        assert "789019" in ciks   # Microsoft
        assert "1045810" in ciks  # NVIDIA

    def test_returns_normalized_strings(self):
        ciks = get_sp500_ciks()
        for cik in ciks:
            # No leading zeros — str(int(cik)) should be identity
            assert cik == str(int(cik))
