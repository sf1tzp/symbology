"""Unit tests for the company CLI's current-fiscal-quarter label (pure logic)."""
from datetime import date

import pytest

from symbology.cli.companies import current_fiscal_quarter_label


@pytest.mark.parametrize(
    "fye, today, expected",
    [
        # Calendar-year filer (Dec 31): quarters track calendar quarters.
        (date(2024, 12, 31), date(2026, 1, 1), "FY2026 Q1"),
        (date(2024, 12, 31), date(2026, 3, 31), "FY2026 Q1"),
        (date(2024, 12, 31), date(2026, 4, 1), "FY2026 Q2"),
        (date(2024, 12, 31), date(2026, 12, 31), "FY2026 Q4"),
        # Apple (late-September FYE): June sits in fiscal Q3, FY named for Sept 2026.
        (date(2025, 9, 26), date(2026, 6, 6), "FY2026 Q3"),
        (date(2025, 9, 26), date(2025, 9, 27), "FY2026 Q1"),  # day after year-end
        # Walmart (Jan 31 FYE): June is ~4 months in -> Q2 of the FY ending Jan 2027.
        (date(2025, 1, 31), date(2026, 6, 6), "FY2027 Q2"),
    ],
)
def test_current_fiscal_quarter_label(fye, today, expected):
    assert current_fiscal_quarter_label(fye, today) == expected


def test_current_fiscal_quarter_label_handles_leap_day_fye():
    # A Feb-29 year-end clamps to Feb 28 in a non-leap year without raising. Mar 1
    # 2025 is the day after that clamped year-end, so it starts FY2026 Q1.
    assert current_fiscal_quarter_label(date(2024, 2, 29), date(2025, 3, 1)) == "FY2026 Q1"
