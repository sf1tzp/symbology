# shellcheck shell=bash
# shellcheck disable=SC2035,SC2050,SC2148,SC1083,SC2164

set dotenv-load


# Run components
cli *ARGS:
    just -d server -f server/justfile cli {{ARGS}}


# Testing
# just test -m integration (run database tests, requires db availability)
test *ARGS:
    just -d server -f server/justfile test {{ARGS}}

# j benchmark production https://symbology.online
# j benchmark staging 10.0.0.21 --insecure-skip-tls-verify
benchmark environment TARGET *ARGS:
  #!/usr/bin/env bash
  k6 run --env TARGET={{TARGET}} {{ARGS}} infra/testing/smoke.{{environment}}.ts

# Linting
lint: lint-server lint-ui

lint-server *ARGS:
    just -d server -f server/justfile lint {{ARGS}}

lint-ui *ARGS:
    just -d ui -f ui/justfile format {{ARGS}}

# The Alembic chain has one external-tool boundary: the `auth` schema is created
# by Alembic (r7b8c9d0e1f2), but the tables inside it are created by Better
# Auth's CLI, and a later Alembic migration (s8c9d0e1f2a3) adds an FK to
# auth."user". So a straight `alembic upgrade head` fails on a fresh DB. This
# sequences the three phases. Safe on an existing DB too: phase 1 is a no-op once
# past the checkpoint, Better Auth's migrate is idempotent, and phase 3 applies
# whatever's pending — so this doubles as the everyday "migrate" entrypoint.
# AUTH_CHECKPOINT (below) is the immutable revision that creates the auth schema.
#
# Bootstrap or incrementally migrate the database (Alembic + Better Auth).
db-init:
    #!/usr/bin/env bash
    set -euo pipefail
    AUTH_CHECKPOINT="r7b8c9d0e1f2"
    echo "==> [1/3] Alembic upgrade to auth-schema checkpoint (${AUTH_CHECKPOINT})"
    just -d server -f server/justfile migrate-to "${AUTH_CHECKPOINT}"
    echo "==> [2/3] Better Auth migrate (creates auth.user, etc.)"
    just -d ui -f ui/justfile auth-migrate
    echo "==> [3/3] Alembic upgrade to head"
    just -d server -f server/justfile migrate

# Dependencies
deps:
    just -d server -f server/justfile deps
    just -d ui -f ui/justfile deps

build-server:
    just -f server/justfile build

build-ui:
    just -f ui/justfile build

deploy HOST: build-ui
    #!/usr/bin/env bash
    set -euo pipefail
    ssh {{HOST}} -C "mkdir -p ~/images"
    ssh {{HOST}} -C "mkdir -p ~/caddyfiles"
    ssh {{HOST}} -C "mkdir -p ~/symbology"
    scp caddyfiles/{{HOST}} {{HOST}}:~/caddyfiles/symbology.caddy
    sops -d secrets/{{HOST}}.env | ssh {{HOST}} "cat > ~/symbology/.env"
    scp symbology-compose.yaml {{HOST}}:~/symbology-compose.yaml
    scp ui/symbology-ui-latest.tar {{HOST}}:~/images/symbology-ui-latest.tar
    ssh {{HOST}} -C "~/.local/bin/nerdctl load -i ~/images/symbology-ui-latest.tar"
    ssh {{HOST}} -C "~/.local/bin/nerdctl compose -f ~/symbology-compose.yaml down"
    ssh {{HOST}} -C "~/.local/bin/nerdctl compose -f ~/symbology-compose.yaml up -d --env-file ~/symbology/.env"

deploy-prod HOST TAG:
    #!/usr/bin/env bash
    set -euo pipefail
    REGISTRY="gitea.zen.lofi"
    REPO="sfi/symbology"
    UI_IMAGE="$REGISTRY/$REPO-ui:{{TAG}}"
    ssh {{HOST}} -C "mkdir -p ~/caddyfiles ~/symbology"
    scp caddyfiles/{{HOST}} {{HOST}}:~/caddyfiles/symbology.caddy
    sops -d secrets/{{HOST}}.env | ssh {{HOST}} "cat > ~/symbology/.env"
    scp symbology-compose.yaml {{HOST}}:~/symbology-compose.yaml
    ssh {{HOST}} -C "~/.local/bin/nerdctl pull $UI_IMAGE"
    ssh {{HOST}} -C "SYMBOLOGY_UI_IMAGE=$UI_IMAGE \
        ~/.local/bin/nerdctl compose -f ~/symbology-compose.yaml down"
    ssh {{HOST}} -C "SYMBOLOGY_UI_IMAGE=$UI_IMAGE \
        ~/.local/bin/nerdctl compose -f ~/symbology-compose.yaml up -d --env-file ~/symbology/.env"

bounce HOST:
    ssh {{HOST}} -C "~/.local/bin/nerdctl compose -f ~/symbology-compose.yaml down"
    ssh {{HOST}} -C "~/.local/bin/nerdctl compose -f ~/symbology-compose.yaml up -d --env-file ~/symbology/.env"


deploy-server HOST: build-server
    #!/usr/bin/env bash
    set -euo pipefail
    ssh {{HOST}} -C "mkdir -p ~/images"
    ssh {{HOST}} -C "mkdir -p ~/symbology"
    sops -d secrets/{{HOST}}.env | ssh {{HOST}} "cat > ~/symbology/.env"
    scp symbology-server-compose.yaml {{HOST}}:~/symbology-server-compose.yaml
    scp server/symbology-server-latest.tar {{HOST}}:~/images/symbology-server-latest.tar
    ssh {{HOST}} -C "~/.local/bin/nerdctl load -i ~/images/symbology-server-latest.tar"
    ssh {{HOST}} -C "~/.local/bin/nerdctl compose -f ~/symbology-server-compose.yaml down"
    ssh {{HOST}} -C "~/.local/bin/nerdctl compose -f ~/symbology-server-compose.yaml up -d --env-file ~/symbology/.env"


# Queue the full ingest → embed → page-content → diff pipeline for a ticker.
queue-new-jobs TICKER LOOKBACK FORM:
    #!/usr/bin/env bash
    set -euo pipefail

    just cli jobs start filing_ingestion --set ticker={{ TICKER }} --set count={{ LOOKBACK }} --set form={{ FORM }} --priority 2

    just cli jobs start company_diff --set ticker={{ TICKER }} --set lookback={{ LOOKBACK }} --set form={{ FORM }} --priority 1 --delay 20

    just cli jobs start company_page_content --set ticker={{ TICKER }} --set lookback={{ LOOKBACK }} --set form={{ FORM }} --priority 3 --delay 45


# Queue a 10-Q (quarterly) page for a ticker. A 10-K stands in for Q4, so the
# quarterly page anchors on the most recent 10-K plus the quarters filed since
# it — the diff and page-content pipelines select that anchor dynamically, so we
# don't compute it here. We just ingest the latest annual (the anchor, with its
# filing page + chunks) and the recent quarters (QUARTERS, default 4 to cover a
# full ≤3-quarter cycle with slack); the company page job self-heals any missing
# filing pages and waits. company_diff/company_page_content take no lookback for
# 10-Q (the pipelines bound it to the cycle themselves).
queue-10q TICKER QUARTERS='4':
    #!/usr/bin/env bash
    set -euo pipefail

    just cli jobs start filing_ingestion --set ticker={{ TICKER }} --set count=1 --set form=10-K --priority 2
    just cli jobs start filing_ingestion --set ticker={{ TICKER }} --set count={{ QUARTERS }} --set form=10-Q --priority 2

    just cli jobs start company_diff --set ticker={{ TICKER }} --set form=10-Q --priority 1 --delay 30

    just cli jobs start company_page_content --set ticker={{ TICKER }} --set form=10-Q --priority 3 --delay 60


# Staggered batch enqueue from a JSON file (array of objects with a `ticker`
# field — build it from the plaintext table with
# `uv run python scripts/fortune500_to_json.py`). Rows whose ticker is
# "Non-public" or empty are skipped. The (filtered) list is sliced into blocks
# of BLOCK_SIZE companies; BLOCK selects which slice to enqueue (1 => the first
# BLOCK_SIZE, 2 => the next BLOCK_SIZE, etc.) so a large file can be drained a
# block at a time. WAVE_SIZE companies go in at once; each later wave is
# deferred WAVE_GAP seconds so we don't flood EDGAR or build one giant FIFO
# backlog. Within a wave the diff track (which gates visibility) is favored via
# priority and content trails it; diff/page wait a little so ingestion lands
# first. NOT idempotent — re-runs re-enqueue everything.
#   just queue-batch server/symbology/data/fortune-500.json 3 20 1   # rows 1-20
#   just queue-batch server/symbology/data/fortune-500.json 3 20 2   # rows 21-40
queue-batch DATA_FILE FORM='10-K' LOOKBACK='3' BLOCK='1'  BLOCK_SIZE='20':
    #!/usr/bin/env bash
    set -euo pipefail

    WAVE_SIZE="1" WAVE_GAP="1400"

    # Block N covers the filtered rows [start, end): start = (N-1)*size.
    start=$(( ({{ BLOCK }} - 1) * {{ BLOCK_SIZE }} ))
    end=$(( {{ BLOCK }} * {{ BLOCK_SIZE }} ))

    total=$(jq '[.[] | select(.ticker != "Non-public" and .ticker != "")] | length' "{{ DATA_FILE }}")

    echo "Enqueuing block {{ BLOCK }} (rows $(( start + 1 ))-${end} of ${total}, waves of ${WAVE_SIZE}, +${WAVE_GAP}s/wave)..."

    # jq filters out non-public tickers, slices the block, and emits
    # "<index>\t<ticker>" where <index> is block-relative (0-based) so the wave
    # math restarts each block rather than relying on a counter the pipe's
    # subshell would swallow.

    jq -r --argjson start "${start}" --argjson end "${end}" \
        '[.[] | select(.ticker != "Non-public" and .ticker != "")][$start:$end] | to_entries[] | "\(.key)\t\(.value.ticker)"' "{{ DATA_FILE }}" \
    | while IFS=$'\t' read -r idx ticker; do
        wave=$(( idx / WAVE_SIZE ))
        delay=$(( wave * WAVE_GAP ))
        head=$(( delay + 30 ))   # diff/page wait ~30s for ingestion to land first
        echo ">> ${ticker} (wave ${wave}, ingest +${delay}s, diff/page +${head}s)"

        just cli jobs start filing_ingestion \
            --set ticker="${ticker}" --set count={{ LOOKBACK }} --set form={{ FORM }} \
            --priority 2 --delay "${delay}"
        just cli jobs start company_diff \
            --set ticker="${ticker}" --set lookback={{ LOOKBACK }} --set form={{ FORM }} \
            --priority 1 --delay "${head}"
        just cli jobs start company_page_content \
            --set ticker="${ticker}" --set lookback={{ LOOKBACK }} --set form={{ FORM }} \
            --priority 3 --delay "${head}"
    done
