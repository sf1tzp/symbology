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

build component:
  #!/usr/bin/env bash
  if [[ "{{component}}" == "api" ]]; then
    just -d src -f src/justfile build
  elif [[ "{{component}}" == "ui" ]]; then
    just -d ui -f ui/justfile build
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
