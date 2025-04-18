# shellcheck shell=bash
# shellcheck disable=SC2035,SC2050,SC2148

set dotenv-load

_create_venv:
    #!/usr/bin/env bash
    if [[ ! -d .venv ]]; then
        uv venv -p 3.13 .venv
        uv pip install -r requirements.lock
    fi

run component *ARGS:
  #!/usr/bin/env bash
  if [[ "{{component}}" == "api" ]]; then
    just run-api "{{ARGS}}"
  elif [[ "{{component}}" == "ingest" ]]; then
    just run-ingest "{{ARGS}}"
  elif [[ "{{component}}" == "ui" ]]; then
    just run-ui "{{ARGS}}"
  elif [[ "{{component}}" == "db" ]]; then
    just start-db "{{ARGS}}"
  else
    echo "Error: Unknown component '{{component}}'"
    exit 1
  fi

test component *ARGS:
  #!/usr/bin/env bash
  if [[ "{{component}}" == "py" ]]; then
    just test-python "{{ARGS}}"
  elif [[ "{{component}}" == "ui" ]]; then
    just test-ui "{{ARGS}}"
  else
    echo "Error: Unknown component '{{component}}'"
    exit 1
  fi

lint component *ARGS:
  #!/usr/bin/env bash
  if [[ "{{component}}" == "py" ]]; then
    just lint-python "{{ARGS}}"
  elif [[ "{{component}}" == "ui" ]]; then
    just lint-ui "{{ARGS}}"
  else
    echo "Error: Unknown component '{{component}}'"
    exit 1
  fi

import "src/justfile"
import "infra/justfile"
import "ui/justfile"

