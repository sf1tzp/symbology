# LLM Context & Cost Optimization Plan

Tracking issue for reducing Anthropic API costs and improving context utilization
in the SEC filing ingestion and content generation pipeline.

## Context

After running five-year filing ingestions for six companies, we identified several
areas where we're wasting tokens on repeated information, over-powered models for
simple tasks, and misconfigured generation parameters. This plan addresses each
area from highest to lowest impact.

---

## P0: Quick wins (config/code changes)

### 1. Skip LLM calls for already-processed documents
**Est. savings: 80-100% on re-runs**

- [ ] Before calling `handle_content_generation` for single summaries, query for
  existing generated content matching the same (source_document, system_prompt,
  model_config) triple
- [ ] If a match exists, reuse its `content_hash` and skip the API call entirely
- [ ] We already have `content_hash` on documents and `generated_content_document_association` --
  just need the pre-check in `handle_full_pipeline` (handlers.py ~L369-408)

**Files:** `server/symbology/worker/handlers.py`

### 2. Downgrade single summaries from Sonnet to Haiku
**Est. savings: ~10x cost reduction on ~80% of LLM calls**

- [ ] Change `single_summary` model in `PIPELINE_MODEL_CONFIGS` from
  `claude-sonnet-4-5-20250929` to `claude-haiku-4-5-20251001`
- [ ] Before switching, run a side-by-side comparison: generate Haiku single
  summaries for 1-2 companies and diff against existing Sonnet outputs
- [ ] If quality is acceptable, ship the change

Single summaries are structured extraction from one document at a time. Sonnet's
strength (cross-document synthesis) isn't needed here. Reserve Sonnet for the
aggregate stage where it actually adds value.

**Files:** `server/symbology/worker/pipeline.py` (L17-21)

### 3. Lower temperature for factual extraction
**Est. savings: indirect (better outputs, less variance, fewer retries)**

Current default is `temperature: 0.8` across all stages. This is high for tasks
that should be deterministic and faithful to source text.

- [ ] Single summaries: `temperature: 0.2`
- [ ] Aggregate summaries: `temperature: 0.3`
- [ ] Frontpage summaries: `temperature: 0.3`

**Files:** `server/symbology/worker/pipeline.py`, `server/symbology/utils/config.py`

### 4. Right-size max_tokens per stage
**Est. savings: prevents runaway outputs, small direct savings**

Currently `max_tokens: 4096` for all stages, including frontpage which asks for
~100 words.

- [ ] Single summaries: `2048` (structured, focused output)
- [ ] Aggregate summaries: `4096` (multi-year synthesis, keep as-is)
- [ ] Frontpage summaries: `512` (~100 words requested)

**Files:** `server/symbology/worker/pipeline.py` (L17-21)

---

## P1: Observability (required before deeper optimizations)

### 5. Track input/output tokens from API response
**Enables: data-driven optimization, cost attribution per pipeline stage**

The Anthropic API returns `message.usage.input_tokens` and
`message.usage.output_tokens`. We currently ignore these.

- [ ] Update `AnthropicResponseAdapter` to capture `input_tokens` and
  `output_tokens` from the API response
- [ ] Add `input_tokens` and `output_tokens` columns to `generated_content` table
  (new Alembic migration)
- [ ] Store token counts alongside each generated content record
- [ ] Add a CLI command or API endpoint to report token usage per pipeline run

**Files:** `server/symbology/llm/client.py` (L16-24), `server/symbology/database/generated_content.py`

---

## P2: Prompt quality fixes

### 6. Fix market_risk prompt (currently a copy of risk_factors)
**Impact: better outputs, less wasted model reasoning**

`prompts/market_risk/prompt.md` is an exact duplicate of `prompts/risk_factors/prompt.md`.
It asks about "risk factors section" when it should address quantitative market
risk disclosures (interest rate sensitivity, FX exposure, commodity prices).

- [ ] Write a dedicated market risk prompt focused on quantitative disclosures
- [ ] Re-run market_risk single summaries for one company to validate

**Files:** `server/prompts/market_risk/prompt.md`

### 7. Fix typos in prompts
- [ ] `controls_procedures/prompt.md`: "procedutres" -> "procedures",
  "they key componets" -> "the key components"
- [ ] `management_discussion/prompt.md`: trailing " a" on last line

**Files:** `server/prompts/controls_procedures/prompt.md`, `server/prompts/management_discussion/prompt.md`

### 8. Strengthen the aggregate-summary prompt
**Impact: reduces output variance, focuses synthesis on what matters**

Currently just: "Summarize the historical changes in these documents."

- [ ] Specify what constitutes a meaningful "change" (quantitative shifts,
  strategy pivots, new risks, discontinued segments)
- [ ] Define output structure (chronological vs. thematic)
- [ ] Instruct the model to call out when sections are largely unchanged YoY
  instead of restating stable content

**Files:** `server/prompts/aggregate-summary/prompt.md`

---

## P3: Architectural improvements (measure first via P1)

### 9. Pre-process and normalize filing text before storage
**Est. savings: 10-20% input token reduction**

- [ ] Collapse excessive whitespace and blank lines
- [ ] Strip residual HTML entities and formatting artifacts from EDGAR extraction
- [ ] Normalize Unicode characters (smart quotes, em-dashes, etc.)
- [ ] Apply normalization in `ingest_filing_documents` before storing content

**Files:** `server/symbology/ingestion/ingestion_helpers.py`

### 10. Diff-based aggregation instead of full summaries
**Est. savings: 40-60% token reduction at aggregate stage**

Instead of sending 5 full single summaries to the aggregate prompt, send:
- Most recent year's full summary
- Year-over-year diffs for prior years (only what changed)

This directly targets repeated information across years. A company's business
description may be 80% identical year-to-year.

- [ ] Implement a text diff utility that produces human-readable change summaries
- [ ] Modify aggregate content generation to use diff-based input
- [ ] Compare output quality against current full-summary approach

**Files:** `server/symbology/worker/handlers.py`, `server/symbology/llm/prompts.py`

### 11. Complexity router for short/stable sections
**Est. savings: eliminate ~2/3 of calls for simple sections**

`controls_procedures` is typically very short and formulaic ("management assessed...
internal controls are effective"). Running it through the full 3-stage pipeline
(7 LLM calls) is wasteful.

- [ ] Add a document-length threshold check before entering the pipeline
- [ ] For short/stable sections, route to a single-pass summary instead of
  single -> aggregate -> frontpage
- [ ] Make the threshold configurable per document type

**Files:** `server/symbology/worker/handlers.py`, `server/symbology/worker/pipeline.py`
