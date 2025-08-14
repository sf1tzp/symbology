# shellcheck shell=bash
# shellcheck disable=SC2035,SC2050,SC2148,SC1083,SC2164
# set dotenv-load

set dotenv-load

up:
  nerdctl compose -f docker-compose.yaml --env-file .env up -d

down:
  nerdctl compose -f docker-compose.yaml down

logs *ARGS:
  nerdctl compose -f docker-compose.yaml logs {{ARGS}}

deploy environment="staging": _generate-api-types
  ansible-playbook -i infra/inventories/{{environment}} infra/deploy-symbology.yml

# Development resources
run component *ARGS:
  #!/usr/bin/env bash
  if [[ "{{component}}" == "api" ]]; then
    just -d . -f src/justfile run

  elif [[ "{{component}}" == "ingest" ]]; then
    just -d . -f src/justfile ingest {{ARGS}}

  elif [[ "{{component}}" == "generate" ]]; then
    just -d . -f src/justfile generate {{ARGS}}

  elif [[ "{{component}}" == "ui" ]]; then
    just -d ui -f ui/justfile run {{ARGS}}

  elif [[ "{{component}}" == "db" ]]; then
    just -d infra -f infra/justfile up

  else
    echo "Error: Unknown component '{{component}}'" && exit 1
  fi

test component *ARGS:
  #!/usr/bin/env bash
  if [[ "{{component}}" == "api" ]]; then
    just -d . -f src/justfile test {{ARGS}}

  elif [[ "{{component}}" == "ui" ]]; then
    echo "no testing for ui yet"
    just -d ui -f ui/justfile check {{ARGS}}
  else
    echo "Error: Unknown component '{{component}}'" && exit 1

  fi

# j benchmark production https://symbology.online
# j benchmark staging 10.0.0.21 --insecure-skip-tls-verify
benchmark environment TARGET *ARGS:
  #!/usr/bin/env bash
  k6 run --env TARGET={{TARGET}} {{ARGS}} infra/testing/smoke.{{environment}}.ts


lint component *ARGS:
  #!/usr/bin/env bash
  if [[ "{{component}}" == "api" ]]; then
    just -d src -f src/justfile lint {{ARGS}}
  elif [[ "{{component}}" == "ui" ]]; then
    pushd ui
    just lint {{ARGS}}
    popd
  else
    echo "Error: Unknown component '{{component}}'"
    exit 1
  fi

build component: _generate-api-types
  #!/usr/bin/env bash
  if [[ "{{component}}" == "api" ]]; then
    just -d src -f src/justfile build
  elif [[ "{{component}}" == "ui" ]]; then
    just -d ui -f ui/justfile build
  elif [[ "{{component}}" == "images" ]]; then
    just build api
    just build ui
    nerdctl pull postgres:17.4
    nerdctl save symbology-api:latest -o /tmp/symbology-api-latest.tar
    nerdctl save symbology-ui:latest -o /tmp/symbology-ui-latest.tar
    nerdctl save postgres:17.4 -o /tmp/postgres-17.4.tar
  else
    echo "Error: Unknown component '{{component}}'"
    exit 1
  fi

deps component *ARGS:
  #!/usr/bin/env bash
  if [[ "{{component}}" == "api" ]]; then
    just -d src -f src/justfile deps
  elif [[ "{{component}}" == "ui" ]]; then
    just -d ui -f ui/justfile deps
  else
    echo "Error: Unknown component '{{component}}'"
    exit 1
  fi

# Release management (TODO)
_tag version:
  git tag {{version}}
  git push origin tag {{version}}

_untag version:
  git tag -d {{version}}
  git push --delete origin {{version}}

# Database migration commands
db-current: # Show current migration version
  just -d src -f src/justfile _create_venv
  uv run alembic current

db-history: # Show migration history
  just -d src -f src/justfile _create_venv
  uv run alembic history --verbose

db-upgrade TARGET="head": # Apply migrations
  just -d src -f src/justfile _create_venv
  uv run alembic upgrade {{TARGET}}

db-downgrade TARGET: # Rollback to specific migration
  just -d src -f src/justfile _create_venv
  uv run alembic downgrade {{TARGET}}

db-revision MESSAGE: # Create new migration
  just -d src -f src/justfile _create_venv
  uv run alembic revision -m "{{MESSAGE}}"

db-auto-revision MESSAGE: # Auto-generate migration from model changes
  just -d src -f src/justfile _create_venv
  uv run alembic revision --autogenerate -m "{{MESSAGE}}"

db-show-sql TARGET="head": # Show SQL without executing
  just -d src -f src/justfile _create_venv
  uv run alembic upgrade {{TARGET}} --sql

db-stamp VERSION: # Mark migration as applied without running
  just -d src -f src/justfile _create_venv
  uv run alembic stamp {{VERSION}}

db-reset: # Reset to base (WARNING: destructive)
  just -d src -f src/justfile _create_venv
  @echo "⚠️  This will reset the database to base state!"
  @read -p "Are you sure? (y/N): " confirm && [ "$$confirm" = "y" ] || exit 1
  uv run alembic downgrade base

_generate-api-types:
  just -d ui -f ui/justfile generate-api-types