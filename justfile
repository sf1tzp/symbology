# shellcheck shell=bash
# shellcheck disable=SC2035,SC2050,SC2148,SC1083,SC2164
# set dotenv-load

set dotenv-load

deploy environment="staging": _generate-api-types
  ansible-playbook -i infra/inventories/{{environment}} infra/deploy-symbology.yml

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

images ENV: _generate-api-types
  just -f src/justfile build
  nerdctl save symbology-api:latest -o /tmp/symbology-api-latest.tar
  just -f ui/justfile build-for-deploy {{ ENV }}
  nerdctl save symbology-ui:latest -o /tmp/symbology-ui-latest.tar
  nerdctl pull postgres:17.4 # fixme: version pin
  nerdctl save postgres:17.4 -o /tmp/postgres-17.4.tar


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

_generate-api-types:
  just -d ui -f ui/justfile generate-api-types

ingest-pipeline TICKER FORM COUNT DOCUMENT_TYPE:
  #!/usr/bin/env bash
  set -euo pipefail

  set -x
  just run cli companies ingest {{TICKER}}
  just run cli filings ingest {{TICKER}} {{FORM}} {{COUNT}} # todo: make idempotent

  model_config1=$(just run cli model-configs create qwen3:4b --num-ctx 28567 -o json | jq -r '.short_hash')
  model_config2=$(just run cli model-configs create qwen3:14b --num-ctx 8000 -o json | jq -r '.short_hash')
  model_config3=$(just run cli model-configs create gemma3:12b --num-ctx 10000 -o json | jq -r '.short_hash')

  prompt1=$(just run cli prompts create {{DOCUMENT_TYPE}} -o json | jq -r '.short_hash')
  prompt2=$(just run cli prompts create aggregate-summary -o json | jq -r '.short_hash')
  prompt3=$(just run cli prompts create general-summary -o json | jq -r '.short_hash')

  accession_numbers=$(just run cli filings list {{TICKER}} --form {{FORM}} -o json | jq -r '.[] | .accession_number')

  initial_summaries="[]"

  # Check if we have any accession numbers to process
  if [[ -z "$accession_numbers" || "$accession_numbers" == "" ]]; then
    echo "No accession numbers found for {{TICKER}} {{FORM}}, exiting normally"
    exit 0
  fi

  for accession in $accession_numbers; do
    document=$(just run cli documents list "$accession" --document-type {{DOCUMENT_TYPE}} -o json | jq -r '.[0].short_hash')
    single_summary=$(just run cli generated-content create \
      --company {{TICKER}} \
      --description '{{DOCUMENT_TYPE}}_single_summary' \
      --prompt $prompt1 \
      --model-config $model_config1 \
      --source-documents $document -o json | jq -r '.short_hash')

    # Append the single_summary to the initial_summaries array using jq
    initial_summaries=$(echo "$initial_summaries" | jq --arg item "$single_summary" '. += [$item]')
  done

  # Convert JSON array to individual --source-content arguments
  source_content_args=""
  for hash in $(echo "$initial_summaries" | jq -r '.[]'); do
    source_content_args="$source_content_args --source-content $hash"
  done

  aggregate_summary=$(just run cli generated-content create \
    --company {{TICKER}} \
    --prompt $prompt2 \
    --description '{{DOCUMENT_TYPE}}_aggregate_summary' \
    --model-config $model_config2 \
    $source_content_args -o json  | jq -r '.short_hash')

  just run cli generated-content create \
    --company {{TICKER}} \
    --prompt $prompt3 \
    --description '{{DOCUMENT_TYPE}}_frontpage_summary' \
    --model-config $model_config3 \
    --source-content $aggregate_summary

ingest-10k TICKER:
  #!/usr/bin/env bash
  set -euo pipefail
  for document_type in "business_description" "risk_factors" "management_discussion" "controls_procedures"; do
    just ingest-pipeline {{TICKER}} 10-K 5 "$document_type"
  done

ingest-10q TICKER:
  #!/usr/bin/env bash
  set -euo pipefail
  for document_type in "risk_factors" "management_discussion" "controls_procedures" "market_risk"; do
    just ingest-pipeline {{TICKER}} 10-Q 6 "$document_type"
  done

ingest TICKER:
  just ingest-10k {{TICKER}}
  just ingest-10q {{TICKER}}
