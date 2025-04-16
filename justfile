# shellcheck shell=bash
# shellcheck disable=SC2148
set dotenv-load

_create_venv:
    #!/usr/bin/env bash
    if [[ ! -d .venv ]]; then
        uv venv -p 3.13 .venv
        uv pip install -r requirements.lock
    fi

import "src/justfile"
import "infra/justfile"
import "ui/justfile"

