The l1-l4 dirs are empty scaffolds. Here is the synthesized plan.

---

# Implementation Plan: New Content Features (`new-content.md`)

## Overview

This effort expands the generated-content pipeline along four coordinated tracks: (1) reorganizing prompts and model configs into a single declarative `model_configs.yaml` with an `l1/l2/l3/l4` prompt layout; (2) making the worker LLM client provider-agnostic so a model name routes to either the Anthropic API or the internal OpenAI-compatible endpoint; (3) introducing a stored `generation_depth` attribute and extending the chain to an L4 stage with UI display; and (4) adding the full set of new page-content generation types (document change reports, company/group/filing/document page content and intros). The work is overwhelmingly additive: the existing synchronous `handle_full_pipeline` -> composable `pipeline.py` stage functions -> `handle_content_generation` machinery is preserved, with new ContentStage enum values, prompt dirs, model-config entries, and stage functions layered on. No job-graph rework is undertaken (that remains aspirational MEMORY territory). Sequencing (Phase 0 done): the **dual LLM client** is isolated and de-risks everything downstream — it shipped first (with the `pyyaml` dep). The **config reorg (track 1) is deferred** to the new-stages phase: the current prototype prompts (`general-summary`/`frontpage_summary`/`company-group-*`) are being abandoned rather than migrated, and the YAML/loader shape is defined by the new stages, so it is built and the old prompts retired in one pass alongside track 4. The `generation_depth` schema change lands next so new stages store depth at write time; the large page-content expansion lands last on top of all of it. Note `generation_depth` is a heuristic orthogonal to `content_stage` — "L4" just means three generations from a primary source, not a specific stage; the depth-4 content here is Area 2's `company_intro`/`group_intro`.

Current Alembic head verified as `i8e9f0a12b3c`. The `server/prompts/l1..l4/` scaffold directories exist and are empty.

---

## Recommended sequencing

The four areas have real dependencies; landing them in dependency order minimizes rework and keeps each PR dedup-safe and reviewable.

**Phase 0 — Foundations (DONE; no DB schema changes):**
- **Area 4 (Dual LLM client)** — provider dispatch seam in `llm/client.py` keyed on the model name (`claude*` → Anthropic, else → the shared `OPENAI_*` chat endpoint), an `OpenAIResponseAdapter`, `init_openai_chat_client`, and a routing test. All four caller contracts preserved; reuses `settings.openai` (no new config). **Implemented + tested.**
- **Area 3 reduced to the `pyyaml` dependency** (added). The rest of Area 3 (config loader, YAML, flat prompts, vocabulary) is **deferred to the new-stages phase** — see Area 3. Rationale: the old prototype prompts are being abandoned, so migrating them now is wasted motion; the config infra's shape is defined by the new stages, which don't exist yet.

**Phase 1 — Generation-depth schema (prerequisite for L4) — DONE:**
- **Area 1, schema half (implemented):** added the stored, nullable, indexed `generation_depth` column (migration `j9a0b1c2d3e4`, off head `i8e9f0a12b3c`), the shared `compute_generation_depth(source_content)` helper + `GeneratedContent._depth_value()` (stored value, falling back to a chain walk for legacy rows), `to_dict` exposure, and write-time computation at all three create sites: `handle_content_generation` (the seam Area 2 uses), `handle_company_group_pipeline` (analysis), and `generate_group_frontpage_summary`. No backfill (old prototype content is being retired). This is the **hard prerequisite** for Area 2 setting depth per stage. (No `page_subheading` enum value here — depth is a heuristic, not a stage.) Migration authored but not yet applied to the live DB.
- **Why before Area 2:** Area 2 explicitly threads `generation_depth` through `handle_content_generation`; that integration seam should already exist. The enum-add migration pattern is also shared, so establishing the convention once here reduces conflicts.

**Phase 2 — Page-content expansion (the large additive surface):**
- **Area 2 (new generation types)** + **the deferred Area 3 config infra** + **Area 1's UI half**. These add the bulk of new ContentStage values, the config loader + YAML + flat prompts, stage functions, query helpers, and the `handle_full_pipeline` wiring — and **retire the old prototype prompts/stages** (`general-summary`/`frontpage_summary`/`company-group-*`). They depend on: the dual client (Area 4, done) so non-claude models route, and the `generation_depth` column (Area 1 schema) so new rows store depth. The UI surfacing (Area 1) lands here too, after the new stages exist, so the stage-label maps and depth badges cover the full vocabulary in one UI pass.
- **Why last:** It has the most file touch points and the most open questions (naming/aliasing, selective-regen jobs). Building it on settled foundations avoids churn.

Net order: **Phase 0 (Area 4 + pyyaml, DONE) → Area 1 schema (Phase 1) → Area 2 + Area 3 config infra + Area 1 UI (new-stages phase).**

---

## Area 3 — Prompt & Model Config infrastructure (mostly deferred to the new-stages phase)

**Status (decided during Phase 0):** the only Phase-0 piece is the **`pyyaml` dependency — DONE** (added to `pyproject.toml`, locked, synced). Everything else here — `config_loader.py`, `model_configs.yaml`, the flat `ensure_prompt`, and the `{max_tokens, temperature}` vocabulary — is **deferred to the new-stages phase (folded into Area 2)**. Reason: the config's shape (stage keys, prompt paths, per-stage configs) is defined by the *new* stages, which don't exist yet. Migrating the current config into YAML now would only reorganize prompts we're about to delete.

**The current pipeline and its prototype prompts are left untouched and running** through Phases 0/1: `aggregate-summary`, `general-summary`, `company-group-analysis`, `company-group-frontpage`, and the 5 L1 doc-type prompts, plus the three dict literals in `pipeline.py:19-39`. They are retired in the new-stages phase when the pipeline is wired to the new prompts/stages.

**Correction (was wrong in an earlier draft):** `general-summary` is **not** an L1 fallback — it is the prompt for the **L3 `frontpage_summary` stage** (`pipeline.py:30`; L1 summaries use the per-doc-type prompts). `general-summary`/`frontpage_summary` are prototyping names being **abandoned** in favor of the new outline stages, so they are *deleted*, not migrated. Only its `examples/bad-example-extra-intro.md` is droppable under the "retire examples" decision.

**Target prompt tree (end state, after the new-stages phase — old prototype prompts deleted):**

```
prompts/
├── model_configs.yaml
├── l1/  business_description.md  management_discussion.md  market_risk.md  controls_procedures.md  risk_factors.md
├── l2/  change-report.md  filing-main-content.md  document-intro-content.md
├── l3/  change-report-intro.md  company-main-content.md  group-main-content.md  filing-intro-content.md
└── l4/  company-intro-content.md  group-intro-content.md
```

**Work — deferred to the new-stages phase (folded into Area 2):**
1. ~~Add PyYAML dependency~~ — **DONE in Phase 0.**
2. **Add `server/symbology/worker/config_loader.py`** — cached `load_pipeline_config(prompts_dir=None)` returning model_configs/prompts/doc_type_prompts/form_document_types with typed accessors. Validate prompt-file existence and that stage keys are valid ContentStage values; fail loudly on drift.
3. **Flatten `ensure_prompt`** — read a single `{prompts_dir}/{path}.md` instead of `{name}/prompt.md` + globbed `examples/`. (Additive or replacing — see test fallout below.)
4. **Author `server/prompts/model_configs.yaml`** — `model_configs` (per-stage `model` + `options: {max_tokens, temperature}` only — **not** `num_predict`/`num_ctx`, no `top_k`/`top_p`; see #12 — keyed by the new ContentStage values), `prompts` (stage → flat path, e.g. `change_report: l2/change-report`), `doc_type_prompts` (doc type → `l1/{type}`), `form_document_types`. **Build options directly, not via `create_default`** (which injects `top_k`/`top_p`).
5. **Author the flat prompt files** for the new stages per the target tree.
6. **Wire handlers to the loader and retire the old config** — `handle_full_pipeline`/`handle_company_group_pipeline` pull from `config_loader`; delete the three dict literals (`pipeline.py:19-39`) and the deleted prototype prompt dirs.
7. **CLI delegation** — `cli/prompts.py`/`cli/model_configs.py` delegate to the shared loader (minimal, per #7).

**Fallout to handle in the new-stages phase:** `tests/worker/test_handlers.py` (L189/309/367/502) and `tests/worker/test_pipeline.py` (L91/104) construct prompt dirs by the current names in the `{name}/prompt.md` shape and call `ensure_prompt("general-summary", ...)`; `ingest.just:16` references `general-summary`. All must be updated when `ensure_prompt` flattens and the prototype prompts are removed.

**DB/Alembic migrations:** none (new `Prompt`/`ModelConfig` rows created lazily by `ensure_*`).

---

## Area 4 — Worker LLM Client Flexibility (dual Anthropic + OpenAI-compatible) (Phase 0)

**Approach:** Insert a provider dispatch at the single seam in `server/symbology/llm/client.py`, keyed on `model_config.model`. `_provider_for(model)` returns `"anthropic"` if `model.lower().startswith("claude")` else `"openai"`. The only non-claude model in play to start is `google/gemma-4-e4b`. The two public entry points (`get_generate_response`, `get_chat_response`) keep their exact signatures and `(adapter, None)` contract but branch internally. Anthropic keeps the current path; the OpenAI path reuses the proven `embeddings.py` pattern (build `openai.OpenAI(base_url, api_key, timeout)` against the **existing shared `settings.openai` config** — the *same* `OPENAI_*` host/port used for embeddings — call `chat.completions.create` through `retry_backoff`) and wraps the result in a new `OpenAIResponseAdapter` exposing the identical 7 attributes so all four callers (handlers.py:171, handlers.py:341, pipeline.py:374, cli/generated_content.py:178) work unchanged. **One OpenAI-compatible endpoint serves both embeddings and chat; no new config class.** Keeping it simple by design: if a stage is configured for the OpenAI endpoint and the infra isn't running, the pipeline may fail or time out — infra availability is owned **outside** this project. The `openai` SDK (2.38.0) is already a dependency; no DB changes — `model` is already the routing key plumbed through `ModelConfig`/`ensure_model_config`/the new YAML.

**Steps:**
1. **No new config.** Chat reuses the existing `OpenAISettings` (`utils/config.py:47`, `env_prefix="OPENAI_"`): `base_url`/`api_key`/`request_timeout`/`retry_timeout`. The embedding-specific fields (`embedding_model`, `embedding_dimensions`, `embedding_batch_size`) are irrelevant to chat — the chat model name comes from `ModelConfig.model`, not config. The `OPENAI_*` env vars are already present for embeddings, so a deployment that points them at a box also serving `google/gemma-4-e4b` chat needs **zero new env**.
2. **Add `OpenAIResponseAdapter`** in `server/symbology/llm/client.py` taking `(completion, duration_ns)`; map `.response`/`.content` = `completion.choices[0].message.content`, `.total_duration` = `duration_ns/1e9`, `.done`=True, `.done_reason`=`finish_reason`, `.input_tokens`/`.output_tokens` from `completion.usage` with a **None-guard** (some internal servers omit usage → store NULL).
3. **Add `_provider_for(model)` + `init_openai_chat_client(...)`** in client.py, mirroring `embeddings.init_embedding_client` (which already does `cfg = settings.openai`). Import `from openai import OpenAI`; leave Anthropic `init_client()` untouched.
4. **Branch `get_generate_response`/`get_chat_response` on provider** — shared option parsing forwards **only `max_tokens` and `temperature`** from `options_json` to **both** providers (top_k/top_p/num_ctx intentionally dropped — see #12); extract per-provider impls. Anthropic body verbatim. OpenAI generate path prepends `{"role":"system",...}` then `{"role":"user",...}`; chat path passes `messages` directly. Wrap in `OpenAIResponseAdapter`, return `(adapter, None)`. `client=None` still inits the provider-appropriate client (`init_openai_chat_client` uses `settings.openai`). Keep identical structured-logging keys.
5. **Export `init_openai_chat_client` (and `OpenAIResponseAdapter`)** from `server/symbology/llm/__init__.py` for surface coherence (no caller change needed).
6. **Smoke-test routing** (`server/tests/llm/test_client_routing.py`) — assert `_provider_for('claude-haiku-4-5-20251001')=='anthropic'`, `_provider_for('google/gemma-4-e4b')=='openai'`; monkeypatch `messages.create` vs `chat.completions.create` and assert each adapter exposes the 7 attributes. Run with `server/.venv/bin/python -m pytest`.

**New files:** `server/tests/llm/test_client_routing.py`

**DB/Alembic migrations:** none. **Config/secrets:** none — reuses existing `OPENAI_*`.

**Risks:** absent `completion.usage` → AttributeError without the None-guard; `finish_reason` vocabulary differs from Anthropic `stop_reason` (cosmetic — stored opaque, no caller string-matches it); `retry_backoff` catches all exceptions and retries until `retry_timeout` — a 4xx or an offline endpoint blocks the worker for the full timeout (**accepted** per project decision — infra uptime owned externally; still worth a debug log of the underlying exception so the cause is visible); the `claude*` prefix silently routes typos (e.g. `cluade-`) to the OpenAI box — add a per-request debug log of resolved provider; `get_chat_response` has zero callers (covered by smoke test only).

---

## Area 1 — Generation Depth heuristic and site display

Split across **Phase 1 (schema + write-time computation)** and **Phase 2 (UI display, alongside Area 2)**.

**Approach:** `generation_depth` is a **heuristic, orthogonal to `content_stage`**: it counts how many generations separate a piece of content from a primary source (L1-from-docs = 1, each subsequent generation +1). It is **not** a stage name and there is **no single "L4 stage"** — many distinct stages can occupy any depth, and the actual depth-4 content in this effort (`company_intro`, `group_intro`) is produced by **Area 2**'s stages, which inherit depth=4 automatically from the write-time computation below. Today depth is implicit, computed at runtime via `GeneratedContent.get_source_chain_depth()` (generated_content.py:228); make it a **stored, queryable Integer** set at write time, then surface it in the SvelteKit UI as a depth indicator. The existing synchronous FULL_PIPELINE architecture and the five existing enum values are untouched.

> **`page_subheading` is out of scope as a core deliverable.** It was inferred from the illustrative chain line in `new-content.md` (`… → Page Content (l3) → Page Subheading (l4) …`), which illustrates the depth pattern continuing rather than mandating a stage. If/when wanted it is a depth-agnostic prompt (its depth depends on whatever it's generated from) — park it at **`prompts/misc/page-subheading.md`**, add a `page_subheading` ContentStage value, and a generate function then. Not built here. See the optional note at the end of this section.

**Steps (Phase 1 — schema + write-time computation):**
1. **Add `generation_depth` to `GeneratedContent`** — `server/symbology/database/generated_content.py`: `generation_depth: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)` near `content_stage` (~L106); add `"generation_depth": self.generation_depth` to `to_dict()` (~L267). Keep nullable (tolerates legacy/dedup rows); no CHECK constraint. `Integer` already imported (L8).
2. **Alembic migration: add column + index** — following the `a1b2c3d45e6f` add_column/create_index pattern. `op.add_column('generated_content', sa.Column('generation_depth', sa.Integer(), nullable=True))` + `op.create_index('ix_generated_content_generation_depth',...)`. Optional one-time backfill UPDATE keyed off `content_stage` (single_summary=1, aggregate_summary=2, frontpage_summary=3, company_group_analysis=2, company_group_frontpage=3). Letter-prefixed 12-char revision; `down_revision = i8e9f0a12b3c` (current head).
3. **Compute/persist depth in `handle_content_generation`** — `server/symbology/worker/handlers.py`: after source resolution (L150-161), before `content_data` (L187): if source_documents and not source_content → depth=1; else `depth = 1 + max((c.generation_depth or c.get_source_chain_depth()) for c in source_content)` (default 1 if empty). Add `"generation_depth": depth` to content_data. Only set on `was_created=True` to avoid mutating shared dedup rows. **This is the integration seam Area 2 relies on** — every new Area 2 stage gets correct depth for free. Land it here.
4. **Set depth in the group-frontpage direct path** — `generate_group_frontpage_summary` (pipeline.py:341) builds content_data directly via `create_generated_content`; add `"generation_depth": (source_content.generation_depth or 0) + 1` (~L382).

**Steps (Phase 2 — UI display, alongside Area 2):**
5. **Surface depth in UI API/query layer** — add `generation_depth: number | null` to `GeneratedContentSummaryResponse` in `ui/src/lib/api-types.ts` (~L91); add `generation_depth` to the row interface in `ui/src/lib/server/db/types.ts` (L121); add `gc.generation_depth` to `.select([...])` in `ui/src/lib/server/db/generated-content.ts` (L40-49) and `ui/src/lib/server/db/filings.ts` (L75), mapping it into the returned object (generated-content.ts L55-65). (The `ContentStageEnum` union in `types.ts` L10 gains **Area 2's** new stage values, not a `page_subheading` value — coordinate with Area 2.)
6. **Display depth in the content table** — `ui/src/lib/components/content/GeneratedContentTable.svelte`: add a "Depth N" badge near the stage badge (~L106-108) from `gc.generation_depth` (consider a depth→label tooltip, open question #3). Stage labels/variants (`stageLabels` L21-26, `getStageBadgeVariant` L46-60) and `contentLabel()` in `ui/src/lib/server/db/status.ts` (L30) are extended for **Area 2's** new stages — do this jointly with Area 2 in one UI pass.

**Optional (not in this effort) — `page_subheading`:** author `server/prompts/misc/page-subheading.md`; add `PAGE_SUBHEADING = 'page_subheading'` ContentStage (generated_content.py:36) via an `ALTER TYPE content_stage_enum ADD VALUE IF NOT EXISTS 'page_subheading'` migration following `c3d4e5f67a8b`; add a `generate_page_subheading(...)` function modeled on `generate_frontpage_summary` (pipeline.py:290) and wire it where a subheading is actually needed. Depth falls out automatically from step 3.

**New files:** `server/alembic/versions/<rev>_add_generation_depth_to_generated_content.py`.

**DB/Alembic migrations:** add column `generated_content.generation_depth INTEGER NULL` + index; optional backfill UPDATE. (No enum migration in this area — the new depth-4 stages are added by Area 2.)

**Risks:** setting depth on a dedup-returned existing row could conflict if the same content is reached at two depths → write only when `was_created=True` (first-seen wins); `get_source_chain_depth` recursive M2M walk is expensive (max_depth=10) — prefer reading stored `source.generation_depth`, fall back to walk only for legacy nulls; hand-maintained `ContentStageEnum` union in `types.ts` must stay in sync with the Postgres enum (driven by Area 2's additions); backfill mapping is heuristic (group analysis "true" depth is debatable) — the live path is authoritative.

---

## Area 2 — Additional Page Content & Standardization (new generation types) (Phase 2)

**Approach:** Add the new generation kinds on top of the existing 3-stage pipeline. Each is "N source hashes → 1 LLM call → 1 GeneratedContent row tagged with a content_stage", mapping cleanly onto `handle_full_pipeline` → `pipeline.py` composable functions → `handle_content_generation` (handlers.py:103). The work is additive: new ContentStage values, new flat prompt files/`model_configs.yaml` entries (via Area 3's loader), new composable stage functions, and new invocation points. No new orchestration layer. Depth is set per stage level via the `generation_depth` seam landed in Area 1 step 3. The existing two group stages are kept (decide alias vs. distinct via open question).

**Subject/scope FKs (RESOLVED — see open question #8):** the four page types map onto four nullable, indexed *scope* FKs on `GeneratedContent` — `company_id` + `company_group_id` exist today; **add `filing_id` and `document_id`** mirroring `company_id` exactly. These are distinct from the existing *provenance* edges (`source_documents` M2M, `source_content` M2M), which are unchanged and are what `generation_depth` walks. Filing-page content is then a single indexed query on `filing_id` (not M2M recovery); document-scoped content (L1 summary, `document_page_intro`) sets `document_id`, giving `Document` → its content directly. **Backref naming:** `Document.generated_content` is already taken by the `source_documents` M2M backref, so the new `document_id` relationship must use a different name (e.g. `Document.scoped_content`); `Filing` has no such collision. Do **not** model the L1 summary as a hard `Document.l1_summary_id` 1:1 — content-hash dedup (identical docs share a row) and re-runs (new prompt/model → additional `single_summary` rows) break the 1:1; "the L1 summary for a doc" is a *latest `single_summary` scoped to this doc* query.

**Mapping (from `new-content.md`):** Document change reports: l1 doc summary → l2 `change_report` → l3 `change_report_intro`. Company page: l2 business_description change report → l3 `company_main_content` → l4 `company_intro`. Group page: members' l2 business-desc change reports → l3 `group_main_content` → l4 `group_intro`. Filing page: l1 summaries → l2 `filing_main_content` → l3 `filing_intro`. Document page: l1 summary → l2 `document_page_intro`.

**Steps:**
1. **Add new ContentStage values** — `server/symbology/database/generated_content.py`:36-42, lowercase: `change_report`, `change_report_intro`, `company_main_content`, `company_intro`, `group_main_content`, `group_intro`, `filing_main_content`, `filing_intro`, `document_page_intro`. Keep the existing 5 so current rows/queries keep working.
2. **Alembic migration adding the enum values** — following `c3d4e5f67a8b` exactly: one `op.execute("ALTER TYPE content_stage_enum ADD VALUE IF NOT EXISTS '<value>'")` per value, no-op downgrade. Letter+hex revision, `down_revision` = then-current head (after Area 1 migrations). Keep any backfill that *uses* the new values in a **separate** migration (Postgres ADD VALUE cannot be used in the same transaction that references it).
3. **Add the `filing_id` + `document_id` scope FKs** — `generated_content.py`: two nullable, indexed `mapped_column(ForeignKey(...))` mirroring `company_id` (L77) — `filing_id` → `filings.id` (ondelete SET NULL), `document_id` → `documents.id` (ondelete SET NULL) — plus relationships; the `document_id` relationship uses a non-colliding backref (e.g. `Document.scoped_content`). Add both to `to_dict()`. (Column migration listed below.)
4. **Create flat prompt files for new types** — per Area 3's flat layout: `l2/change-report.md`, `l2/filing-main-content.md`, `l2/document-intro-content.md`, `l3/company-main-content.md`, `l3/group-main-content.md`, `l3/filing-intro-content.md`, `l3/change-report-intro.md`, `l4/company-intro-content.md`, `l4/group-intro-content.md`. Map each in `model_configs.yaml` `prompts` (stage → path).
5. **Register model configs** — add `model_configs.yaml` entries keyed by new stages: `change_report`/main-content stages → sonnet/larger output; `*_intro` → haiku/~300-512. (Option-key vocabulary — `num_predict`/`num_ctx` vs `max_tokens` — is tracked in open question #12 with Area 4.)
6. **Add composable stage functions in `pipeline.py`** — modeled on `generate_frontpage_summary` (L290-338): `generate_change_report`, `generate_change_report_intro`, `generate_company_main_content` (sets `company_id`), `generate_company_intro`, `generate_filing_main_content`/`generate_filing_intro` (set `filing_id`), `generate_document_page_intro` (sets `document_id`), plus group main/intro (set `company_group_id`). Each calls `handle_content_generation` with the right `source_content_hashes` + `content_stage`, passes `generation_depth` per level, and sets the appropriate scope FK.
7. **Thread `generation_depth` through `handle_content_generation`** — `handlers.py`:103-215 builds content_data at L187; read optional `params['generation_depth']` (or stage→level map) and store it. This reuses Area 1's seam; guard the assignment so it is safe if the column is absent, but the end-state is to set it here. Likewise read optional `params['filing_id']`/`params['document_id']` and persist the scope FK.
8. **Extend `handle_full_pipeline` to emit new content** — `handlers.py`:437-634: after l1/l2/l3 per-(form,doc_type) outputs, (a) capture the l2 change_report hash per (form,doc_type); (b) group l1 hashes by filing → `generate_filing_main_content` → `generate_filing_intro` (set `filing_id`); (c) per l1 summary → `generate_document_page_intro` (set `document_id`); (d) take business_description l2 change_report hash → `generate_company_main_content` → `generate_company_intro`. Thread hashes forward as `agg_hash`→`fp_hash` is today (L579-595); update counters.
9. **Re-point group pipeline to consume l2 change reports** — `handle_company_group_pipeline` (handlers.py:272-396) currently uses `get_aggregate_summaries_by_ticker` (generated_content.py:473). Add `get_change_reports_by_ticker(ticker, document_type=business_description)` and write `group_main_content` (l3) + `group_intro` (l4) via new stage functions, setting `company_group_id`. Keep or alias the existing analysis/frontpage path (open question).
10. **Add read-side query helpers per page type** — `generated_content.py`, mirroring `get_aggregate_summaries_by_ticker`/`get_company_group_frontpage_summary` (L473,864): `get_company_main_content`/`get_company_intro` (by `company_id`+stage), `get_filing_main_content`/`get_filing_intro` (by `filing_id`+stage — direct, no M2M), `get_document_page_intro` (by `document_id`+stage), `get_change_report`.
11. **Wire enqueue paths only if selective regen is needed** — simplest path reuses `JobType.FULL_PIPELINE`/`COMPANY_GROUP_PIPELINE` (jobs.py:27-36); defer new JobTypes unless selective regeneration is required (then add `ALTER TYPE job_type_enum ADD VALUE` + thin `@register_handler` + enqueue from `cli/pipeline.py` L114/L325).

**New files:** `server/alembic/versions/<rev>_add_page_content_stages.py`, `server/alembic/versions/<rev>_add_generated_content_scope_fks.py`; flat prompts `server/prompts/l2/change-report.md`, `l2/filing-main-content.md`, `l2/document-intro-content.md`, `l3/company-main-content.md`, `l3/group-main-content.md`, `l3/filing-intro-content.md`, `l3/change-report-intro.md`, `l4/company-intro-content.md`, `l4/group-intro-content.md`

**DB/Alembic migrations:** add the 9 new `content_stage_enum` values (no-op downgrade); **add `generated_content.filing_id` + `generated_content.document_id` nullable FK columns + indexes** (mirror `company_id`); no new JobType unless selective regen.

**Risks:** naming/aliasing collision — doc renames `aggregate_summary`→"change report" / `frontpage_summary`→"change report intro" but existing rows, `get_aggregate_summaries_by_ticker` (with its description-LIKE fallback), and the group pipeline still reference old names; adding-without-retiring avoids breakage but creates two vocabularies — keep queries consistent; ADD VALUE cannot be used in the same transaction that writes it (keep backfills separate); the new `document_id` relationship must avoid the `Document.generated_content` backref already claimed by the `source_documents` M2M; scope FKs are set per content kind (NULL otherwise) so writers must set the right one — a stage that forgets its scope FK silently produces unqueryable content; combinatorial growth of rows/LLM cost (dedup by content_hash mitigates, `force=True` regenerates all).

---

## Area 5 — Page pipelines & PageContent (publishing layer)

**Concept:** separate the immutable **generation layer** (`GeneratedContent` — content-hash deduped, append-only) from a versioned **publishing layer** (`PageContent`). A `*_page_content_pipeline` run produces a new immutable `*PageContent` row pointing at the specific generated pieces composing that page. "Current" = latest row per scope by `created_at`; history retained for rollback/audit/sweeping republish. (The page-pipeline *decomposition* — replacing `handle_full_pipeline` with composable per-page pipelines — is deferred; the data types are designed first.)

**Decisions (confirmed):** four **separate** tables per page type (not polymorphic) so each page can evolve independently; **all-relational** slots (no JSON); **provenance via M2M to domain entities**; scalar content slots as nullable FKs → `generated_content.id`; the company change-report map **retains both the report and its intro** per doc_type.

**Schema:**

```
document_page_content
  id PK | document_id FK→documents (scope)
  summary_content_id FK→generated_content (L1 single_summary)
  intro_content_id   FK→generated_content (L2 document_page_intro)
  created_at | index (document_id, created_at DESC)
  -- provenance = the scope document; no list

filing_page_content
  id PK | filing_id FK→filings (scope)
  main_content_id  FK→generated_content (L2 filing_main_content)
  intro_content_id FK→generated_content (L3 filing_intro)
  created_at | index (filing_id, created_at DESC)
filing_page_content_document (M2M provenance)  -- source documents
  filing_page_content_id FK, document_id FK, PK(both)

company_page_content
  id PK | company_id FK→companies (scope)
  main_content_id  FK→generated_content (L3 company_main_content)
  intro_content_id FK→generated_content (L4 company_intro)
  created_at | index (company_id, created_at DESC)
company_page_content_change_report (map slot)  -- report + intro per doc_type
  company_page_content_id FK, document_type document_type_enum,
  change_report_id FK→generated_content (L2),
  change_report_intro_id FK→generated_content (L3, nullable),
  PK(company_page_content_id, document_type)
company_page_content_filing (M2M provenance)   -- source filings
  company_page_content_id FK, filing_id FK, PK(both)

group_page_content
  id PK | company_group_id FK→company_groups (scope)
  main_content_id  FK→generated_content (L3 group_main_content)
  intro_content_id FK→generated_content (L4 group_intro)
  created_at | index (company_group_id, created_at DESC)
group_page_content_company (M2M provenance)    -- member companies
  group_page_content_id FK, company_id FK, PK(both)
```

**Conventions:**
- Content-slot FKs → `generated_content`: **`ondelete RESTRICT`** (a published snapshot must not dangle). Child/M2M rows: **`ondelete CASCADE`** from their parent page row.
- Versioning: new row per pipeline run, immutable; "current" = latest by `created_at` per scope. Read helpers `get_current_{company,group,filing,document}_page_content(scope_id)` become the **render path**, replacing the per-stage "latest-by-stage" helpers (chunk 3). The scope FKs on `GeneratedContent` remain for gathering/admin ("regenerate everything about X").
- Group page's source change-reports are **not** stored on the row — reachable via `group_main_content`'s `GeneratedContent.source_content`. Only domain-entity provenance (member companies) lives on the page.
- Models in a new `server/symbology/database/page_content.py` (four classes + association tables); one migration creates all tables.
- **Open sub-decision:** denormalize `content_hash` onto scalar slots? Default **no** (one join away via FK; keeps snapshots normalized).

**Impact on earlier chunks:** chunk 3's `generate_*` stage functions still produce `GeneratedContent` unchanged; chunk 3's *read* helpers are superseded by the `get_current_*_page_content` helpers here. The page-content tables + assembly become a new chunk; the orchestration that calls page pipelines and publishes `PageContent` folds into the (deferred) pipeline-decomposition work.

---

## Open questions for the user (deduped across areas)

1. ~~**Stage naming / standardization.**~~ **RESOLVED:** adopt outline-matching names as **new** ContentStage values (`change_report`, `change_report_intro`, `company_main_content`, `company_intro`, `group_main_content`, `group_intro`, `filing_main_content`, `filing_intro`, `document_page_intro`); old values (`aggregate_summary`, etc.) are **left in the enum** (Postgres can't easily drop values; legacy rows still reference them). New pipeline emits only the new stages. Prompt files renamed freely per the flat tree in Area 3 — no hash-parity / data migration.
2. ~~**`generation_depth` storage.**~~ **RESOLVED (implemented):** stored, **nullable**, indexed column computed at write time; runtime `get_source_chain_depth()` retained only as the legacy fallback in `_depth_value()`. No NOT NULL / server_default / backfill — nullable tolerates legacy rows and the old content is being retired anyway.
3. **Depth display format:** raw "Depth 4" number, or a named tier (L1 Summary / L2 Aggregate / L3 Page Content / L4 Subheading)? Determines whether the UI needs a depth→label map separate from the stage label.
4. ~~**L4 scope / definition.**~~ **RESOLVED:** "L4" is purely the depth heuristic (3 generations from a primary source), **not** a stage. `generation_depth` is orthogonal to `content_stage`; multiple stages can sit at any depth. The depth-4 content here is Area 2's `company_intro`/`group_intro`, which get depth=4 automatically from Area 1's write-time computation. `page_subheading` is dropped as a core deliverable → optional `prompts/misc/page-subheading.md`.
5. ~~**Prompt layout & YAML stage keys.**~~ **RESOLVED:** flat `prompts/l{n}/{name}.md` (one self-contained file per prompt, no per-prompt subdir, no `examples/` concat), explicit data-driven paths in YAML keyed by the new ContentStage values. Built in the new-stages phase, not Phase 0 (see Area 3). The current prototype prompts (`general-summary` = the L3 `frontpage_summary` prompt, **not** an L1 fallback; `aggregate-summary`; `company-group-*`) are left running until then, then deleted — not migrated.
6. ~~**ModelConfig seeding.**~~ **RESOLVED:** keep **lazy upsert only** (`ensure_model_config`/`ensure_prompt` create-by-hash on first use; a run never fails for a missing config). No `sync` CLI in Phase 0 (the catalog/labeling justification is gone — per-instance provenance via `GeneratedContent.model_config_id` already covers "what config made this content"; the stage→config mapping lives in the YAML/git). A `sync` command remains an optional future nicety. **No `name`/`label` column on `ModelConfig`** — dropped.
7. ~~**CLI refactor scope.**~~ **RESOLVED:** minimal — `cli/prompts.py`/`cli/model_configs.py` just delegate to the shared `config_loader`/`ensure_*` assembly path; no broader refactor this effort.
8. ~~**Filing association.**~~ **RESOLVED:** add **scope FKs** `filing_id` *and* `document_id` to `generated_content` (nullable, indexed, mirroring `company_id`), completing the company/group/filing/document quartet that maps to the four page types. Distinct from the provenance M2M (`source_documents`/`source_content`), which is unchanged. `document_id` relationship uses a non-colliding backref (`Document.generated_content` is taken). No hard `l1_summary_id` 1:1 — dedup + re-runs break it; "L1 summary for a doc" is a latest-`single_summary`-scoped-to-doc query.
9. ~~**Selective regeneration.**~~ **RESOLVED:** defer — reuse `FULL_PIPELINE`/`COMPANY_GROUP_PIPELINE` (dedup-safe via content_hash); no new JobTypes or CLI entrypoints this phase. (No `job_type_enum` migration.)
10. ~~**OpenAI chat endpoint topology.**~~ **RESOLVED:** a **single shared `OPENAI_*` endpoint** serves both embeddings and chat — chat reuses `settings.openai` directly, **no new config class** and no new env. Whichever box that host/port points at (ollama or lmstudio) is expected to serve both Jina embeddings and `google/gemma-4-e4b` chat. Infra uptime is owned outside this project; a configured-but-offline endpoint may fail/time out the pipeline, by design.
11. ~~**Non-claude model strings + routing breadth.**~~ **RESOLVED:** only `google/gemma-4-e4b` to start. Routing is `claude*` → Anthropic, everything else → the OpenAI chat box (catch-all `else`, incl. typos — mitigated by a per-request resolved-provider debug log).
12. ~~**Option-key vocabulary.**~~ **RESOLVED:** canonical `options_json` is just `{max_tokens, temperature}`, both forwarded to **both** providers. Drop `top_k`/`top_p` (too granular to tune now) and the doc's Ollama-native `num_predict`/`num_ctx` (not request params on either API path). `num_ctx` remains a possible future OpenAI-path-only escape hatch via `extra_body`.

---

## Consolidated database migrations checklist

All migrations are Alembic, letter-prefixed 12-char revision IDs, chained off current head `i8e9f0a12b3c`. Sequence them in phase order.

- [ ] **(Area 3)** No migration — config reorg is code/YAML only.
- [ ] **(Area 4)** No migration — provider dispatch is code/config only.
- [ ] **(Area 1, Phase 1)** `<rev>_add_generation_depth_to_generated_content.py` — `op.add_column('generated_content', sa.Column('generation_depth', sa.Integer(), nullable=True))` + `op.create_index('ix_generated_content_generation_depth', 'generated_content', ['generation_depth'])`; downgrade drops index then column. `down_revision = i8e9f0a12b3c`. Follows `a1b2c3d45e6f` pattern.
- [ ] **(Area 1, Phase 1, optional)** One-time backfill UPDATE of `generation_depth` from `content_stage` (single_summary=1, aggregate_summary=2, frontpage_summary=3, company_group_analysis=2, company_group_frontpage=3). Separate migration; heuristic only.
- [ ] **(Optional, not this effort)** `page_subheading` ContentStage value — `ALTER TYPE content_stage_enum ADD VALUE IF NOT EXISTS 'page_subheading'`, no-op downgrade, lowercase. Follows `c3d4e5f67a8b`. Only if the optional `misc/page-subheading.md` prompt is built.
- [ ] **(Area 2, Phase 2)** `<rev>_add_page_content_stages.py` — `ALTER TYPE content_stage_enum ADD VALUE IF NOT EXISTS` for `change_report`, `change_report_intro`, `company_main_content`, `company_intro`, `group_main_content`, `group_intro`, `filing_main_content`, `filing_intro`, `document_page_intro`; no-op downgrade. Any backfill *using* these values must be in a **separate** migration (Postgres ADD-VALUE-in-transaction caveat).
- [ ] **(Area 2, Phase 2)** `<rev>_add_generated_content_scope_fks.py` — add `generated_content.filing_id` (FK `filings.id`, ondelete SET NULL) and `generated_content.document_id` (FK `documents.id`, ondelete SET NULL), both nullable, each with an index; mirror `company_id`. Downgrade drops indexes then columns. (Resolved per open question #8.)
- [ ] **(Area 2, Phase 2, conditional)** `ALTER TYPE job_type_enum ADD VALUE` (lowercase) — only if open question 9 chooses selective-regeneration JobTypes.

After each phase, re-run `alembic heads` to capture the new head for the next phase's `down_revision`.
