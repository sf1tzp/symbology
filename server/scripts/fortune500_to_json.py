"""Convert the Fortune 500 plaintext table to JSON.

The source is a tab-separated file with 11 columns and no header:
rank, name, sector, revenue, market_cap, employees, city, state, ceo, ticker,
website. The `ticker` field drives `just queue-batch` (rows whose ticker is
"Non-public" are skipped there).

    uv run python scripts/fortune500_to_json.py                 # txt -> json (defaults)
    uv run python scripts/fortune500_to_json.py in.txt out.json # explicit paths
"""

import json
import sys
from pathlib import Path

# server/symbology/data/ relative to this script (server/scripts/).
DATA_DIR = Path(__file__).resolve().parent.parent / "symbology" / "data"
DEFAULT_IN = DATA_DIR / "fortune-500.txt"
DEFAULT_OUT = DATA_DIR / "fortune-500.json"

FIELDS = [
    "rank",
    "name",
    "sector",
    "revenue",
    "market_cap",
    "employees",
    "city",
    "state",
    "ceo",
    "ticker",
    "website",
]


def parse_row(line: str) -> dict:
    cols = line.rstrip("\n").split("\t")
    if len(cols) != len(FIELDS):
        raise ValueError(f"expected {len(FIELDS)} columns, got {len(cols)}")
    row = {field: value.strip() for field, value in zip(FIELDS, cols)}
    # `rank` is the only naturally-numeric field; keep the rest as strings so
    # "$716.9B" / "1,556,000" survive verbatim.
    if row["rank"].isdigit():
        row["rank"] = int(row["rank"])
    return row


def main() -> None:
    args = sys.argv[1:]
    src = Path(args[0]) if len(args) > 0 else DEFAULT_IN
    dst = Path(args[1]) if len(args) > 1 else DEFAULT_OUT

    rows = []
    with src.open(encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                rows.append(parse_row(line))
            except ValueError as e:
                print(f"skipping line {n}: {e}", file=sys.stderr)

    dst.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {len(rows)} companies -> {dst}")


if __name__ == "__main__":
    main()
