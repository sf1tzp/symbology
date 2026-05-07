# shellcheck shell=bash
# shellcheck disable=SC2035,SC2050,SC2148,SC1083,SC2164

set dotenv-load

secrets-local:
    sops -d secrets/local.env > .env

edit-secrets HOST:
    sops secrets/{{HOST}}.env

# Run components
run-api *ARGS:
    just -d server -f server/justfile run {{ARGS}}

cli *ARGS:
    just -d server -f server/justfile cli {{ARGS}}

run-worker *ARGS:
    just -d server -f server/justfile worker {{ARGS}}

run-scheduler *ARGS:
    just -d server -f server/justfile scheduler {{ARGS}}

run-pipeline-trigger *ARGS:
    just -d server -f server/justfile cli pipeline trigger {{ARGS}}

run-ui *ARGS:
    just -d ui -f ui/justfile up {{ARGS}}

run-db:
    just -d infra -f infra/justfile up

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
lint: lint-api lint-ui

lint-api *ARGS:
    just -d server -f server/justfile lint {{ARGS}}

lint-ui *ARGS:
    just -d ui -f ui/justfile lint {{ARGS}}

# Dependencies
deps-api:
    just -d server -f server/justfile deps

deps-ui:
    just -d ui -f ui/justfile deps

_generate-api-types:
    just -d ui -f ui/justfile generate-api-types

build:
    just -f ui/justfile build
    just -f server/justfile build

deploy HOST:
    #!/usr/bin/env bash
    set -euo pipefail
    ssh {{HOST}} -C "mkdir -p ~/images"
    ssh {{HOST}} -C "mkdir -p ~/caddyfiles"
    ssh {{HOST}} -C "mkdir -p ~/symbology"
    scp caddyfiles/{{HOST}} {{HOST}}:~/caddyfiles/symbology.caddy
    sops -d secrets/{{HOST}}.env | ssh {{HOST}} "cat > ~/symbology/.env"
    scp symbology-compose.yaml {{HOST}}:~/symbology-compose.yaml
    scp ui/symbology-ui-latest.tar {{HOST}}:~/images/symbology-ui-latest.tar
    scp server/symbology-api-latest.tar {{HOST}}:~/images/symbology-api-latest.tar
    ssh {{HOST}} -C "~/.local/bin/nerdctl load -i ~/images/symbology-ui-latest.tar"
    ssh {{HOST}} -C "~/.local/bin/nerdctl load -i ~/images/symbology-api-latest.tar"
    ssh {{HOST}} -C "~/.local/bin/nerdctl compose -f ~/symbology-compose.yaml down"
    ssh {{HOST}} -C "~/.local/bin/nerdctl compose -f ~/symbology-compose.yaml up -d --env-file ~/symbology/.env"

deploy-prod HOST TAG:
    #!/usr/bin/env bash
    set -exuo pipefail
    REGISTRY="gitea.zen.lofi"
    REPO="sfi/symbology"
    UI_IMAGE="$REGISTRY/$REPO-ui:{{TAG}}"
    API_IMAGE="$REGISTRY/$REPO-api:{{TAG}}"
    ssh {{HOST}} -C "mkdir -p ~/caddyfiles ~/symbology"
    scp caddyfiles/{{HOST}} {{HOST}}:~/caddyfiles/symbology.caddy
    sops -d secrets/{{HOST}}.env | ssh {{HOST}} "cat > ~/symbology/.env"
    scp symbology-compose.yaml {{HOST}}:~/symbology-compose.yaml
    ssh {{HOST}} -C "~/.local/bin/nerdctl pull $UI_IMAGE"
    ssh {{HOST}} -C "~/.local/bin/nerdctl pull $API_IMAGE"
    ssh {{HOST}} -C "SYMBOLOGY_UI_IMAGE=$UI_IMAGE SYMBOLOGY_API_IMAGE=$API_IMAGE \
        ~/.local/bin/nerdctl compose -f ~/symbology-compose.yaml down"
    ssh {{HOST}} -C "SYMBOLOGY_UI_IMAGE=$UI_IMAGE SYMBOLOGY_API_IMAGE=$API_IMAGE \
        ~/.local/bin/nerdctl compose -f ~/symbology-compose.yaml up -d --env-file ~/symbology/.env"

bounce HOST:
    ssh {{HOST}} -C "~/.local/bin/nerdctl compose -f ~/symbology-compose.yaml down"
    ssh {{HOST}} -C "~/.local/bin/nerdctl compose -f ~/symbology-compose.yaml up -d --env-file ~/symbology/.env"
