# shellcheck shell=bash
# shellcheck disable=SC2035,SC2050,SC2148,SC1083,SC2164

set dotenv-load

# Run components
run-api *ARGS:
    just -d server -f server/justfile run {{ARGS}}

run-cli *ARGS:
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
test *ARGS:
    just -d server -f server/justfile test {{ARGS}}

# j benchmark production https://symbology.online
# j benchmark staging 10.0.0.21 --insecure-skip-tls-verify
benchmark environment TARGET *ARGS:
  #!/usr/bin/env bash
  k6 run --env TARGET={{TARGET}} {{ARGS}} infra/testing/smoke.{{environment}}.ts

# Linting
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
    scp Caddyfile {{HOST}}:~/caddyfiles/symbology.caddy
    scp symbology-compose.yaml {{HOST}}:~/symbology-compose.yaml
    scp ui/symbology-ui-latest.tar {{HOST}}:~/images/symbology-ui-latest.tar
    scp server/symbology-api-latest.tar {{HOST}}:~/images/symbology-api-latest.tar
    ssh {{HOST}} -C "~/.local/bin/nerdctl load -i ~/images/symbology-ui-latest.tar"
    ssh {{HOST}} -C "~/.local/bin/nerdctl load -i ~/images/symbology-api-latest.tar"
    ssh {{HOST}} -C "~/.local/bin/nerdctl compose -f ~/symbology-compose.yaml down"
    ssh {{HOST}} -C "~/.local/bin/nerdctl compose -f ~/symbology-compose.yaml up -d --env-file ~/symbology/.env"

bounce HOST:
    ssh {{HOST}} -C "~/.local/bin/nerdctl compose -f ~/symbology-compose.yaml down"
    ssh {{HOST}} -C "~/.local/bin/nerdctl compose -f ~/symbology-compose.yaml up -d --env-file ~/symbology/.env"
