# Replacing the Python web API with SvelteKit

A focused opinion on the proposed refactor. **Bottom line: this is a good
move and a relatively low-risk one, because your architecture already has
the right seam to make it clean.** The jobs table is doing the work of
separating "ingestion" from "web", and it should keep doing that. Everything
above the seam (FastAPI → SvelteKit endpoints → DB reads → UI) is fair game;
everything below it (Python workers, LLM pipeline, EDGAR ingestion) stays.

This doc covers:
1. Why the seam works
2. What you actually gain (and what you don't)
3. Concrete stack recommendation
4. What stays Python
5. The four risks worth pre-empting
6. A migration sequence

---

## 1. The seam: jobs table + postgres schema

You already separated concerns the right way. Looking at
`server/symbology/database/jobs.py`:

- `claim_next_job()` uses `SELECT FOR UPDATE SKIP LOCKED` against the `jobs`
  table — this is the canonical postgres job-queue pattern, and it's
  language-agnostic. Any process that can run a SQL transaction can
  enqueue or claim a job.
- The web side currently calls `create_job(...)` to enqueue work. Workers
  poll. There's no in-process coupling between the two; they communicate
  through a row.
- All schema is owned by Alembic. Migrations are *infrastructure*, not
  *application*. They survive whatever language the web layer is in.

This means a TS web layer doesn't need to "talk to FastAPI" — it just talks
to the same postgres database, including the same jobs table. The
FastAPI process is doing two things today that can be cleanly separated:

| What FastAPI does | Where it goes in the new world |
|---|---|
| Read endpoints (companies, filings, documents, generated content, search, groups, financials) | SvelteKit `+page.server.ts` / `+server.ts` reading postgres directly |
| Job enqueue endpoints (trigger ingestion, regenerate analysis) | SvelteKit `+server.ts` writes a row into `jobs` |
| Job status polling | SvelteKit `+server.ts` reads `jobs` |
| Schema/migrations | Stays in Alembic (the Python world) |

The web tier becomes *thin*. The pipeline and worker tier stays *thick*
and Python.

---

## 2. What you actually gain

### 2.1 Big win: SSR over CSR for an editorial product

The mockups you've signed off on are **editorial** in their information
architecture — long-form analysis, citations, side-by-side diffs, dense
tables. These render dramatically better as server-rendered HTML than as
client-fetched JSON. With SvelteKit you get:

- First contentful paint with the company detail page fully rendered
- Real `<a>` tags that pre-paint on hover (link-prefetching is built in)
- View-transitions for the Company → Filing → Change Analysis flow

Today's setup is "browser fetches HTML, then JS, then JSON, then renders."
That's three round-trips before the user sees content. With
`+page.server.ts`, it's one.

### 2.2 Type safety from DB to UI

This is more material than it sounds. The shape of `GeneratedContent` is
the same shape your UI renders. With FastAPI + Pydantic + a hand-typed
TS client, you have three definitions of that shape and reality says they
drift. With a TS query builder against a generated DB schema, there is
exactly one source of truth: the postgres schema. Your UI gets compile-time
errors when a column moves.

### 2.3 One fewer service to operate

FastAPI is fine, but it's a process with its own deploy, logs, healthchecks,
TLS, and dependency tree. Folding it into the SvelteKit node process
removes a moving part. The ingestion workers stay separate — they should
— but the *web tier* collapses to one app.

### 2.4 One language for the people doing UI work

Frontend devs who tweak a route's data shape don't need to write a Python
endpoint, a Pydantic schema, *and* a TS type. They write a Drizzle query
and the type is implied. The "Python expertise to ship a UI feature" tax
goes to zero.

### 2.5 What you don't gain

- **Performance.** FastAPI is already fast for thin DB-bound work. Don't
  expect node + postgres to be measurably quicker than Python + postgres.
  The speedup comes from *fewer round-trips* (SSR), not from a faster
  runtime.
- **Less code.** The total LOC count doesn't change much. You're replacing
  ~12 Python route modules with ~12 TS server endpoints.
- **Simpler deploys overall.** You still have to deploy a Python worker
  fleet. The web tier is simpler; the system isn't.

---

## 3. Recommended stack

I'd land on this exact combination:

```
SvelteKit 2 (already in ui/)
  + node-postgres ('pg')
  + Drizzle ORM (or Kysely — see §3.1)
  + drizzle-kit introspect → generated schema from existing DB
  + Zod for HTTP boundary validation only (not internal)
```

### 3.1 Drizzle vs Kysely

Both are good. Pick one, don't mix.

- **Drizzle** — schema-as-code (TS file), good for projects where TS owns
  the schema. Slightly nicer ergonomics, slightly more opinionated.
- **Kysely** — pure query builder, no schema-as-code. Better fit when
  *someone else* (Alembic) owns the schema and you just want typed
  queries against it.

For your situation, **Kysely is probably the right pick**. Alembic owns
your schema; you don't want two competing source-of-truth files. Kysely
has a `kysely-codegen` tool that introspects postgres and produces a TS
types file — run it after every migration, commit the output, done. Your
queries get full type-safety against the real DB schema without TS having
opinions about what the schema *should* be.

If you find Kysely too verbose, Drizzle's `drizzle-kit introspect` does
the same job but writes a richer schema file. The trade-off is that
Drizzle then *thinks* it owns the schema; you have to keep the
introspected file in lockstep with Alembic. Doable but more friction.

### 3.2 Where data loaders live

- `+page.server.ts` for page data — server-only, runs on every navigation.
- `+server.ts` for the few endpoints that aren't tied to a page (e.g.
  search-as-you-type, job-enqueue, citation chunk fetch).
- Reusable query functions in `ui/src/lib/server/db/*.ts` — these are the TS
  cousins of `server/symbology/database/*.py`. One file per entity,
  exporting typed query functions.

### 3.3 What replaces Pydantic schemas

Almost nothing, internally. Drizzle/Kysely's inferred types replace 80% of
what Pydantic was doing. For the **HTTP boundary** (search query params,
job-enqueue payloads), use Zod — a small, focused schema lib. That's the
only place runtime validation matters; internal calls between server
loaders and DB queries are compile-time-checked.

### 3.4 Streaming

If you're rendering long LLM-generated content, use SvelteKit's
streaming-server-loaders feature. Return the metadata immediately and a
promise for the body; the page renders with a skeleton and resolves the
body when ready. This is a UX feature you can't easily replicate from a
JSON API.

---

## 4. What stays Python

Be specific about the line:

- `server/symbology/ingestion/` — EDGAR fetch + parsing, stays Python.
- `server/symbology/llm/` — LLM client, prompts, response handling, stays
  Python. The prompts dir is a directory of `.md` files, language-neutral.
- `server/symbology/worker/` — the worker loop that polls jobs, stays
  Python.
- `server/symbology/scheduler/` — cron jobs that enqueue ingestion work,
  stays Python.
- `server/symbology/database/` — Python *models* stay, because the workers
  read/write them. But you don't need to keep them in sync with TS types
  — Kysely introspects the actual database, not the Python models. As long
  as Alembic migrations are the source of truth for both, you're fine.
- `server/alembic/` — schema migrations, stays.
- `server/symbology/api/` — **goes**. This is the only directory that
  gets retired.

The CLI tooling in `server/symbology/cli/` and `server/symbology/bin/`
also stays — those are operator tools, not user-facing.

---

## 5. The four risks worth pre-empting

### 5.1 Schema drift between Python models and TS queries

**Risk:** Alembic migration adds a column. Python models updated. TS
queries unaware. UI breaks silently because Kysely still has stale types.

**Mitigation:** Make `kysely-codegen` part of the migration workflow. Add
a `justfile` recipe that runs `alembic upgrade head` followed by
`kysely-codegen`, and commit the generated types file alongside the
migration. CI fails if the types file is stale.

### 5.2 Long-running operations

Some current endpoints presumably do "trigger generation, wait for it to
finish, return result" inline. If so, those endpoints need to become
"enqueue job, return job ID, frontend polls". Look for handlers in
`server/symbology/api/routes/pipeline.py` and `generated_content.py`
that take more than ~200ms — those are the candidates.

**Mitigation:** Audit current FastAPI handlers for sync work that should
be async. Wrap them in `create_job(...)` patterns. The frontend gets a
job-status polling pattern (or SSE / WebSocket) instead of a blocking
HTTP call. This is a UX improvement either way, but it's *required*
before retiring FastAPI for those routes.

### 5.3 PostgreSQL features you're already using

The schema uses several postgres features that need to keep working:

- **`tsvector` + triggers** for search. These are SQL-level, language-
  agnostic — they work from any client. Verify they're declared in
  Alembic migrations (`e4a1b3c56d9f_add_fts_search_vectors.py` suggests
  they are), not in Python application code.
- **Enums** (`JobStatus`, `JobType`, `DocumentType`, `ContentStage`,
  `ContentSourceType`). Kysely-codegen handles postgres enums fine —
  you get a TS union type per enum. Just be aware that the *Python* enums
  (`server/symbology/database/jobs.py`) and the TS introspected types
  need to stay aligned via Alembic.
- **`uuid7`** for IDs. node-postgres returns these as strings — fine for
  the UI which treats them as opaque. Don't try to parse them.
- **`SELECT FOR UPDATE SKIP LOCKED`** for `claim_next_job`. Kysely
  supports `.forUpdate().skipLocked()` natively. If the web tier ever
  needs to claim its own jobs (it probably shouldn't), this still works.

### 5.4 Testing

You have `server/tests/api/` — a presumably large test suite for the
FastAPI routes. Don't try to port it. Instead:

- Keep the Python tests for the database layer (`server/tests/database/`)
  and the ingestion/worker tests. Those are testing things that stay
  Python.
- Write fresh TS tests against the new SvelteKit endpoints using
  `vitest` + the `@sveltejs/kit` test utilities. The DB they hit is a
  test postgres; use Alembic to set the schema, run a fixtures script,
  and tear down. This is a chance to fix any pain points in the old
  test setup, not to faithfully reproduce it.

---

## 6. Migration sequence

Don't do a big-bang cutover. Stand both web tiers up side-by-side and
move routes over one at a time. Here's the order I'd take:

### Phase 0 · Set up parallel infra

- Add `pg`, `kysely`, `kysely-codegen`, `zod` to `ui/package.json`.
- Wire up DB connection in `ui/src/lib/server/db.ts`. Use SvelteKit's
  `$env/dynamic/private` for the connection string.
- Run `kysely-codegen` against your dev DB; commit the generated
  `src/lib/server/db/schema.ts`.
- Add a `justfile` recipe: `migrate` runs Alembic *and* regenerates the
  Kysely types.
- Stand up SvelteKit alongside FastAPI behind your dev reverse proxy
  (nginx/Caddy/Traefik). Both running, no traffic yet on the TS side.

### Phase 1 · Port the read-only routes

In this order — start with the highest-value route and work down:

1. **Company detail** (`/c/:ticker`) — biggest visual upgrade, simple
   data flow (one company, its filings, its generated content), no
   mutations. Build the entire `+page.server.ts` loader, render the
   editorial UI you've mocked, ship it. This proves the pattern.
2. **Filing detail** (`/f/:accession`) — same shape, simpler.
3. **Generated content / change analysis** (`/g/:ticker/:sha`) — slightly
   different because of the sources/citations sidecar.
4. **Companies index** (`/companies`) — pagination + search-as-you-type.
5. **Groups index + detail** (`/groups`, `/groups/:slug`) — group
   synthesis, member list, eventually the risk matrix.
6. **Search** (`/search`) — universal FTS with type filters.
7. **FAQ + landing** — trivially static after the design tokens land.

After Phase 1, every read path has been moved. FastAPI still serves any
write endpoints.

### Phase 2 · Port the write/enqueue routes (1 week)

Routes like "regenerate analysis", "trigger ingestion for ticker X". These
become POSTs to `+server.ts` endpoints that:

1. Validate the payload (Zod).
2. Insert a row into `jobs` via Kysely.
3. Return the job ID.

The frontend already gets the job-status polling pattern from before.

### Phase 3 · Retire FastAPI (a few days)

- Stop routing traffic to the FastAPI process.
- Remove `server/symbology/api/` and `server/symbology/api/routes/`.
- Update deploy config to remove the FastAPI service.
- Update `pyproject.toml` to drop FastAPI / Pydantic / Uvicorn from prod
  deps (keep them in dev deps if useful for ad-hoc work).

### Total elapsed: ~4-5 weeks

…running in parallel with frontend work, so it doesn't really add
calendar time to the broader push if the frontend rebuild is already
happening.

---

## 7. The one architectural decision worth pausing on

Where does the "what filings exist for this company" query live?

Option A (recommended): SvelteKit reads `filings` table directly via
Kysely. The Python ingestion process writes to it. They never know about
each other.

Option B: SvelteKit calls a remaining Python service for this. Don't do
this. It rebuilds the API tier you're trying to retire, just in a
different shape.

The temptation toward Option B comes up when you want "business logic"
in Python that shouldn't live in the web tier. The answer is almost
always: that business logic belongs in a *worker*, triggered by a job,
writing its result back to a table the web tier reads. The web tier
should be presentation + queries. If you find yourself wanting it to do
more, that's the signal to enqueue a job instead.

---

## 8. What if you find postgres-level joins aren't enough?

You're going to hit a few queries that are hard to express in Kysely
because they involve multiple steps, intermediate computation, or
cross-table aggregation. Two escape hatches:

1. **Postgres views.** For complex read shapes (e.g. "top 10 companies
   by change-count in the last 90 days"), define a view in an Alembic
   migration, introspect it as a regular table in Kysely. The query
   logic lives in SQL, the TS layer treats it as a flat read.
2. **SQL files.** Kysely supports raw SQL with parameter binding for
   things that don't fit the builder. Keep these in `src/lib/server/db/
   queries/*.sql` so they're code-reviewable.

Don't reach for an ORM (Drizzle, Prisma) to solve this. The query is the
abstraction.

---

## Summary

- **Do it.** The job queue is the right seam; the schema is the contract;
  postgres is the integration point.
- **Use Kysely + kysely-codegen** so Alembic stays the schema's source of
  truth.
- **SSR everything via `+page.server.ts`.** That's the user-visible win.
- **Keep ingestion and workers in Python.** Don't try to rewrite the LLM
  pipeline.
- **Migrate one route at a time** behind a reverse proxy. Both tiers live
  in parallel for a few weeks.

The mockups I built assume server-rendered pages. They'll render well
either way, but they'll render *fast* on SvelteKit-with-DB-access. The
faster they render, the more often analysts use Symbology to dip in for
a quick check instead of waiting for a research note — and that's the
behavior you want.
