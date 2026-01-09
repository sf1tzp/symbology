# shellcheck shell=bash
# shellcheck disable=SC2035,SC2050,SC2148,SC1083,SC2164
# set dotenv-load

set dotenv-load

# Development resources
run component *ARGS:
  #!/usr/bin/env bash
  if [[ "{{component}}" == "api" ]]; then
    uv run -m src.api.main {{ARGS}}

  elif [[ "{{component}}" == "cli" ]]; then
    uv run -m src.cli.main {{ARGS}}

  elif [[ "{{component}}" == "ui" ]]; then
    just -d ui -f ui/justfile up {{ARGS}}

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
    just -d ui -f ui/justfile lint {{ARGS}}
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

_generate-api-types:
  just -d ui -f ui/justfile generate-api-types

build:
  just -f ui/justfile build
  just -f src/justfile build

deploy HOST:
    scp Caddyfile {{HOST}}:~/Caddyfile
    scp symbology-compose.yaml {{HOST}}:~/symbology-compose.yaml
    scp ui/symbology-ui-latest.tar {{HOST}}:~/symbology-ui-latest.tar
    scp src/symbology-api-latest.tar {{HOST}}:~/symbology-api-latest.tar
    ssh {{HOST}} -C "~/.local/bin/nerdctl load -i symbology-ui-latest.tar"
    ssh {{HOST}} -C "~/.local/bin/nerdctl load -i symbology-api-latest.tar"
    ssh {{HOST}} -C "~/.local/bin/nerdctl compose -f ~/symbology-compose.yaml down"
    ssh {{HOST}} -C "~/.local/bin/nerdctl compose -f ~/symbology-compose.yaml up -d --env-file ~/.env"

