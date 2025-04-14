# shellcheck shell=bash
# shellcheck disable=SC2148
set dotenv-load

_create_venv:
    #!/usr/bin/env bash
    if [[ ! -d .venv ]]; then
        uv venv -p 3.13 .venv
        uv pip install -r requirements.lock
    fi

deps:
    uv pip compile pyproject.toml -o requirements.lock
    uv pip install -r requirements.lock

run *ARGS: _create_venv
    uv run run.py {{ARGS}}

test: _create_venv
    uv run -m pytest --cov=src.ingestion src/tests

lint *FLAGS:
    ~/.local/share/nvim/mason/bin/ruff check src/ingestion {{FLAGS}}

start-db: _generate-pgadmin-config
    #!/usr/bin/env bash
    nerdctl compose --env-file .env -f infra/database.yaml up --detach
    # Wait for PostgreSQL to be ready
    sleep 2
    # Create the symbology database only if it doesn't exist
    nerdctl exec postgres psql -U postgres -c "SELECT 1 FROM pg_database WHERE datname = 'symbology'" | grep -q 1 || nerdctl exec postgres psql -U postgres -c 'CREATE DATABASE symbology;'

stop-db:
    nerdctl compose -f infra/database.yaml down

logs-db *FLAGS:
    nerdctl compose -f infra/database.yaml logs {{FLAGS}}

_generate-pgadmin-config:
    #!/usr/bin/env bash
    mkdir -p infra/pgadmin-data

    # Generate pgadmin-servers.json using jq
    jq -n \
      --arg name "Symbology Database" \
      --arg host "postgres" \
      --arg port "${POSTGRES_PORT:-5432}" \
      --arg db "${POSTGRES_DB:-postgres}" \
      --arg user "${POSTGRES_USER:-postgres}" \
      '{
        "Servers": {
          "1": {
            "Name": $name,
            "Group": "Servers",
            "Host": $host,
            "Port": $port,
            "MaintenanceDB": $db,
            "Username": $user,
            "SSLMode": "prefer",
            "PassFile": "/pgpass",
            "Comment": "Symbology application database"
          }
        }
      }' > infra/pgadmin-data/pgadmin-servers.json

    # Generate pgpass file from environment variables
    echo "postgres:${POSTGRES_PORT:-5432}:postgres:${POSTGRES_USER:-postgres}:${POSTGRES_PASSWORD:-adminpassword}" >> infra/pgadmin-data/pgpass
    echo "postgres:${POSTGRES_PORT:-5432}:symbology:${POSTGRES_USER:-postgres}:${POSTGRES_PASSWORD:-adminpassword}" >> infra/pgadmin-data/pgpass

    # Set correct permissions for pgpass file
    chmod 600 infra/pgadmin-data/pgpass

    echo "PGAdmin configuration files created successfully"
