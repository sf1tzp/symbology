# shellcheck shell=bash
# shellcheck disable=SC2035,SC2050,SC2148,SC1083,SC2164

set dotenv-load

# Job-queuing recipes (queue-ingest-all, queue-batch, queue-new-jobs, queue-10q)
# live here; imported so they're invokable from the repo root and can call `cli`.
import 'ingest.just'


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
    just -d ui -f ui/justfile lint {{ARGS}}

# Read-only UI lint for CI: fails on formatting drift instead of rewriting.
lint-ui-check *ARGS:
    just -d ui -f ui/justfile lint-check {{ARGS}}

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

# Runs db-init (Alembic + Better Auth) then regenerates the UI's kysely DB types,
# so src/lib/server/db/types.ts stays in sync with the schema. Run after adding a
# migration.
#
# Migrate the database and refresh the UI's generated DB types.
migrate: db-init
    just -d ui -f ui/justfile generate-db-types

# Dependencies
deps:
    just -d server -f server/justfile deps
    just -d ui -f ui/justfile deps

build-server:
    just -f server/justfile build

build-ui:
    just -f ui/justfile build

deploy-ui HOST: build-ui
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

