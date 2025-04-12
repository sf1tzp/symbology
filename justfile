set dotenv-load

_create_venv:
    #!/usr/bin/env bash
    if [[ ! -d .venv ]]; then
        uv venv -p 3.13 .venv
        uv pip install -r requirements.txt
    fi

run TICKERS DATE="2020-01-01:": _create_venv
    #!/usr/bin/env bash
    uv run management_discussion_summary.py --tickers {{TICKERS}} --date {{DATE}}

local-db:
    #!/usr/bin/env bash
    nerdctl compose --env-file .env -f infra/database.yaml up --detach

stop-db:
    #!/usr/bin/env bash
    nerdctl compose --env-file .env -f infra/database.yaml down
