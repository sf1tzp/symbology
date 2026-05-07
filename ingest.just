
ingest-pipeline TICKER FORM COUNT DOCUMENT_TYPE:
  #!/usr/bin/env bash
  set -euo pipefail

  set -x
  just run-cli companies ingest {{TICKER}}
  just run-cli filings ingest {{TICKER}} {{FORM}} {{COUNT}} # todo: make idempotent

  model_config1=$(just run-cli model-configs create qwen3:4b --num-ctx 28567 -o json | jq -r '.short_hash')
  model_config2=$(just run-cli model-configs create qwen3:14b --num-ctx 8000 -o json | jq -r '.short_hash')
  model_config3=$(just run-cli model-configs create gemma3:12b --num-ctx 10000 -o json | jq -r '.short_hash')

  prompt1=$(just run-cli prompts create {{DOCUMENT_TYPE}} -o json | jq -r '.short_hash')
  prompt2=$(just run-cli prompts create aggregate-summary -o json | jq -r '.short_hash')
  prompt3=$(just run-cli prompts create general-summary -o json | jq -r '.short_hash')

  accession_numbers=$(just run-cli filings list {{TICKER}} --form {{FORM}} -o json | jq -r '.[] | .accession_number')

  initial_summaries="[]"

  # Check if we have any accession numbers to process
  if [[ -z "$accession_numbers" || "$accession_numbers" == "" ]]; then
    echo "No accession numbers found for {{TICKER}} {{FORM}}, exiting normally"
    exit 0
  fi

  for accession in $accession_numbers; do
    document=$(just run-cli documents list "$accession" --document-type {{DOCUMENT_TYPE}} -o json | jq -r '.[0].short_hash')
    single_summary=$(just run-cli generated-content create \
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

  aggregate_summary=$(just run-cli generated-content create \
    --company {{TICKER}} \
    --prompt $prompt2 \
    --description '{{DOCUMENT_TYPE}}_aggregate_summary' \
    --model-config $model_config2 \
    $source_content_args -o json  | jq -r '.short_hash')

  just run-cli generated-content create \
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
