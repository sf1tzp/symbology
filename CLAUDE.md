# Symbology

SEC filing analysis platform with LLM-powered content generation.

## Project Structure

- `server/` - Python backend (FastAPI, SQLAlchemy, Alembic, Anthropic LLM pipeline)
- `ui/` - Frontend (SvelteKit)
- `infra/` - Infrastructure (Docker compose, Caddy, k6 benchmarks)

## Justfile Recipes

All recipes use `just` (aliased as `j`). The root justfile delegates to server/ui.

### Root (`justfile`)

| Recipe | Description |
|---|---|
| `just run-api` | Start the API server |
| `just cli <ARGS>` | Run CLI commands (e.g. `just cli pipeline trigger AAPL`) |
| `just run-worker` | Start the background job worker |
| `just run-scheduler` | Start the job scheduler |
| `just run-pipeline-trigger <ARGS>` | Shortcut for `cli pipeline trigger` |
| `just run-ui` | Start the UI dev server |
| `just run-db` | Start the database (via infra/) |
| `just test <ARGS>` | Run server tests (`just test -m integration` for DB tests) |
| `just benchmark <env> <target>` | Run k6 benchmarks |
| `just lint-api` | Lint server code |
| `just lint-ui` | Lint UI code |
| `just deps-api` | Install server dependencies |
| `just deps-ui` | Install UI dependencies |
| `just build` | Build both UI and API container images |
| `just deploy <HOST>` | Deploy to a remote host |
| `just bounce <HOST>` | Restart containers on a remote host |

### Server (`server/justfile`)

| Recipe | Description |
|---|---|
| `just run` | Start the FastAPI server (`uv run -m symbology.api.main`) |
| `just cli <ARGS>` | Run CLI commands (`uv run -m symbology.cli.main`) |
| `just test <ARGS>` | Run pytest with coverage (unit by default, `-m integration` for DB) |
| `just migrate` | Run Alembic migrations (`alembic upgrade head`) |
| `just migration-create <message>` | Create new Alembic migration (autogenerate) |
| `just migration-status` | Show current Alembic revision |
| `just worker` | Start the background job worker |
| `just scheduler` | Start the job scheduler |
| `just lint [--fix]` | Run ruff linter |
| `just deps` | Compile and install dependencies via uv |
| `just build` | Build API container image |

### UI (`ui/justfile`)

| Recipe | Description |
|---|---|
| `just up` | Start SvelteKit dev server |
| `just lint` | Run UI linter |
| `just generate-api-types` | Generate TypeScript types from API schema |
| `just build` | Build UI container image |

## Testing

```bash
just test              # unit tests (no DB required)
just test -m integration  # integration tests (requires running DB)
just test -k test_name    # run specific test
```

## Database Migrations

```bash
just -f server/justfile migrate                    # apply migrations
just -f server/justfile migration-create "desc"    # create new migration
just -f server/justfile migration-status           # check current revision
```
