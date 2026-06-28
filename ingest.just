# Job-queuing recipes for ingestion / pipeline work. Imported by the root justfile
# (`import 'ingest.just'`), so invoke them from the repo root — e.g.
# `just queue-ingest-all` — which is where the `cli` recipe these call lives.


# Queue the full ingest → embed → page-content → diff pipeline for a ticker.
# (Embeddings and filing-pair diffs auto-enqueue at ingestion, so we only queue
# ingestion + the company page; the page job self-heals its filing-page deps.)
queue-new-jobs TICKER LOOKBACK FORM:
    #!/usr/bin/env bash
    set -euo pipefail

    just cli jobs start filing_ingestion --set ticker={{ TICKER }} --set count={{ LOOKBACK }} --set form={{ FORM }} --priority 1

    just cli jobs start company_page_content --set ticker={{ TICKER }} --set lookback={{ LOOKBACK }} --set form={{ FORM }} --priority 3 --delay 45


# Queue a 10-Q (quarterly) page for a ticker. A 10-K stands in for Q4, so the
# quarterly page anchors on the most recent 10-K plus the quarters filed since
# it — the diff and page-content pipelines select that anchor dynamically, so we
# don't compute it here. We just ingest the latest annual (the anchor, with its
# filing page + chunks) and the recent quarters (QUARTERS, default 4 to cover a
# full ≤3-quarter cycle with slack); the company page job self-heals any missing
# filing pages and waits. company_page_content takes no lookback for 10-Q (the
# pipeline bounds it to the cycle itself). Diffs auto-enqueue at ingestion.
queue-10q TICKER QUARTERS='4':
    #!/usr/bin/env bash
    set -euo pipefail

    just cli jobs start filing_ingestion --set ticker={{ TICKER }} --set count=1 --set form=10-K --priority 1
    just cli jobs start filing_ingestion --set ticker={{ TICKER }} --set count={{ QUARTERS }} --set form=10-Q --priority 1

    just cli jobs start company_page_content --set ticker={{ TICKER }} --set form=10-Q --priority 3 --delay 60


# Staggered batch enqueue from a JSON file (array of objects with a `ticker`
# field — build it from the plaintext table with
# `uv run python scripts/fortune500_to_json.py`). Rows whose ticker is
# "Non-public" or empty are skipped. The (filtered) list is sliced into blocks
# of BLOCK_SIZE companies; BLOCK selects which slice to enqueue (1 => the first
# BLOCK_SIZE, 2 => the next BLOCK_SIZE, etc.) so a large file can be drained a
# block at a time. WAVE_SIZE companies go in at once; each later wave is
# deferred WAVE_GAP seconds so we don't flood EDGAR or build one giant FIFO
# backlog. The company page trails ingestion by a short delay so the filings
# land first (diffs auto-enqueue at ingestion). NOT idempotent — re-runs
# re-enqueue everything.
#   just queue-batch server/symbology/data/fortune-500.json 3 20 1   # rows 1-20
#   just queue-batch server/symbology/data/fortune-500.json 3 20 2   # rows 21-40
queue-batch  BLOCK='1' BLOCK_SIZE='2':
    #!/usr/bin/env bash
    set -euo pipefail

    DATA_FILE="server/symbology/data/fortune-500.json"
    WAVE_SIZE="1" WAVE_GAP="2400"
    LOOKBACK='5'

    # Block N covers the filtered rows [start, end): start = (N-1)*size.
    start=$(( ({{ BLOCK }} - 1) * {{ BLOCK_SIZE }} ))
    end=$(( {{ BLOCK }} * {{ BLOCK_SIZE }} ))

    total=$(jq '[.[] | select(.ticker != "Non-public" and .ticker != "")] | length' "$DATA_FILE")

    echo "Enqueuing block {{ BLOCK }} (rows $(( start + 1 ))-${end} of ${total}, waves of ${WAVE_SIZE}, +${WAVE_GAP}s/wave)..."

    # jq filters out non-public tickers, slices the block, and emits
    # "<index>\t<ticker>" where <index> is block-relative (0-based) so the wave
    # math restarts each block rather than relying on a counter the pipe's
    # subshell would swallow.

    jq -r --argjson start "${start}" --argjson end "${end}" \
        '[.[] | select(.ticker != "Non-public" and .ticker != "")][$start:$end] | to_entries[] | "\(.key)\t\(.value.ticker)"' "$DATA_FILE" \
    | while IFS=$'\t' read -r idx ticker; do
        wave=$(( idx / WAVE_SIZE ))
        delay=$(( wave * WAVE_GAP ))
        head=$(( delay + 30 ))   # company page waits ~30s for ingestion to land first
        echo ">> ${ticker} (wave ${wave}, ingest +${delay}s, page +${head}s)"

        just cli jobs start filing_ingestion \
            --set ticker="${ticker}" --set count="${LOOKBACK}" --set form=10-K \
            --priority 1 --delay "${delay}"

        just cli jobs start filing_ingestion \
            --set ticker="${ticker}" --set count=6 --set form=10-Q \
            --priority 1 --delay "${delay}"

        just cli jobs start company_page_content \
            --set ticker="${ticker}" --set lookback="${LOOKBACK}" --set form=10-K \
            --priority 3 --delay "${head}"

        # just cli jobs start company_page_content \
        #     --set ticker="${ticker}" --set form=10-Q \
        #     --priority 3 --delay "${head}"
    done


# Queue filing_ingestion (10-K + 10-Q) for EVERY public company in the dataset —
# ingestion ONLY (no diff / page content), to survey what filings & documents we
# actually have. Diffs now auto-enqueue at ingestion; page content can be queued
# separately once the data picture is clear.
#
# The worker count already bounds EDGAR concurrency; WAVE_GAP just spreads the
# PENDING backlog (and EDGAR load) into a ramp instead of one spike — company
# `idx` (0-based over the filtered list) is bucketed into waves of WAVE_SIZE, each
# wave deferred WAVE_GAP seconds via --delay. Rows with ticker "Non-public"/"" are
# skipped. NOT idempotent (re-enqueues), but filing_ingestion upserts, so a re-run
# is harmless.
#   just queue-ingest-all                                                   # defaults (463 cos)
#   just queue-ingest-all server/symbology/data/fortune-500.json 8 8 10 30  # deeper history
queue-ingest-all DATA_FILE='server/symbology/data/fortune-500.json' ANNUAL_COUNT='6' QUARTERLY_COUNT='6' WAVE_SIZE='10' WAVE_GAP='600':
    #!/usr/bin/env bash
    set -euo pipefail

    total=$(jq '[.[] | select(.ticker != "Non-public" and .ticker != "")] | length' "{{ DATA_FILE }}")
    echo "Queueing filing ingestion for ${total} companies (10-K x{{ ANNUAL_COUNT }}, 10-Q x{{ QUARTERLY_COUNT }}; waves of {{ WAVE_SIZE }}, +{{ WAVE_GAP }}s/wave)..."

    jq -r '[.[] | select(.ticker != "Non-public" and .ticker != "")] | to_entries[] | "\(.key)\t\(.value.ticker)"' "{{ DATA_FILE }}" \
    | while IFS=$'\t' read -r idx ticker; do
        wave=$(( idx / {{ WAVE_SIZE }} ))
        delay=$(( wave * {{ WAVE_GAP }} ))
        echo ">> ${ticker} (wave ${wave}, +${delay}s)"

        just cli jobs start filing_ingestion \
            --set ticker="${ticker}" --set count={{ ANNUAL_COUNT }} --set form=10-K \
            --priority 1 --delay "${delay}"
        just cli jobs start filing_ingestion \
            --set ticker="${ticker}" --set count={{ QUARTERLY_COUNT }} --set form=10-Q \
            --priority 1 --delay "${delay}"
    done
