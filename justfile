set dotenv-load

_create_venv:
    #!/usr/bin/env bash
    if [[ ! -d .venv ]]; then
        uv venv -p 3.13 .venv
        uv pip install -r requirements.txt
    fi

venv: _create_venv
    #!/usr/bin/env bash
    source .venv/bin/activate

run TICKERS DATE="2020-01-01:": venv
    #!/usr/bin/env bash
    uv run management_discussion_summary.py --tickers {{TICKERS}} --date {{DATE}}

serve-ai model:
    #!/usr/bin/env bash
    source $HOME/vllm/.venv/bin/activate
    vllm serve --host ${OPEN_AI_HOST} --port ${OPEN_AI_PORT} {{model}}


local-db:
    #!/usr/bin/env bash
    nerdctl compose --env-file .env -f infra/database.yaml up --detach

stop-db:
    #!/usr/bin/env bash
    nerdctl compose --env-file .env -f infra/database.yaml down
