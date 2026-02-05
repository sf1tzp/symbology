# Plan: Restructure Repo into 3 Services

Reorganize the monorepo from `src/` + `ui/` into `collector/` + `api/` + `ui/`.

## Step 1: Move `src/` to `collector/`

```bash
git mv src collector
```

## Step 2: Rename all Python imports `src.` → `collector.`

Mass find-and-replace across all `.py` files under `collector/`:
- `from src.` → `from collector.`
- `import src.` → `import collector.`

Also fix 2 bare imports:
- `collector/database/utils.py`: `from utils.config` → `from collector.utils.config`
- `collector/tests/database/fixtures.py`: `from utils.config` → `from collector.utils.config`

~55 Python files affected, all mechanical replacements.

## Step 3: Update `collector/pyproject.toml`

- `name = "symbology"` → `name = "symbology-collector"`
- `testpaths = ["src/tests"]` → `testpaths = ["collector/tests"]`
- `norecursedirs = ["src/tests/ingestion"]` → `norecursedirs = ["collector/tests/ingestion"]`
- `known-first-party = ["symbology"]` → `known-first-party = ["collector"]`

## Step 4: Update `collector/Dockerfile`

- Line 40: `COPY . /app/src/` → `COPY . /app/collector/`
- Line 55: `CMD ["python", "-m", "src.api.main"]` → `CMD ["python", "-m", "collector.api.main"]`

## Step 5: Update `collector/justfile` (was `src/justfile`)

- `uv run -m src.api.main` → `uv run -m collector.api.main`
- `uv run -m src.bin.*` → `uv run -m collector.bin.*`
- `--cov=src.*` → `--cov=collector.*`
- `src/tests/` → `collector/tests/`
- Docker image: `symbology-api` → `symbology-collector`

## Step 6: Update root `justfile`

- `uv run -m src.api.main` → `uv run -m collector.api.main`
- `uv run -m src.cli.main` → `uv run -m collector.cli.main`
- `src/justfile` → `collector/justfile`
- `-d src` → `-d collector`
- `src/symbology-api-latest.tar` → `collector/symbology-collector-latest.tar`
- Build recipe: add commented-out Go API build
- Deploy recipe: update tar file paths and image names

## Step 7: Update `symbology-compose.yaml`

- Change `symbology-api` service image from `symbology-api` to `symbology-collector`
- Keep container_name as `symbology-api` (so Caddy routing still works during transition)
- Add commented-out Go API service definition

## Step 8: Scaffold Go API (`api/`)

Create minimal Go service structure:

```
api/
  cmd/api/main.go           # HTTP server with /health endpoint
  internal/
    config/config.go         # Env-based config (placeholder)
    database/database.go     # pgx connection (placeholder)
    handlers/
      health.go              # Health handler
      companies.go           # Placeholder
      documents.go           # Placeholder
      filings.go             # Placeholder
      generated_content.go   # Placeholder
      model_configs.go       # Placeholder
      prompts.go             # Placeholder
    middleware/
      cors.go                # CORS (placeholder)
      logging.go             # Request logging (placeholder)
    router/router.go         # Route registration (placeholder)
  Dockerfile                 # Multi-stage Go build
  go.mod                     # module github.com/sf1tzp/symbology/api
  justfile                   # build/run/test recipes
```

`main.go` will be a working server with just a `/health` endpoint. All other files are minimal placeholders with package declaration and TODO comments.

## Step 9: No changes to `ui/`, `prompts/`, `infra/`, `Caddyfile`, `ingest.just`

- `ui/` stays as-is (API host configured by env var, doesn't care if backend is Python or Go)
- `prompts/` stays at repo root (loaded by CLI from filesystem, not Python imports)
- `infra/` stays at repo root
- `Caddyfile` routes to container name `symbology-api`, which stays unchanged
- `ingest.just` uses `just run cli ...` which delegates to root justfile (already updated in Step 6)

## Verification

1. `cd /home/deployer/symbology && just run api` - Python API starts
2. `just run cli --help` - CLI works
3. `just test api` - Tests pass
4. `cd api && go build ./cmd/api` - Go scaffold compiles
5. `cd collector && nerdctl build -t symbology-collector:latest .` - Docker build works

## Files Modified

| Category | Count | Files |
|----------|-------|-------|
| Git move | 1 | `git mv src collector` |
| Python imports | ~55 | All `.py` files under `collector/` |
| Config/infra | 5 | `collector/pyproject.toml`, `collector/Dockerfile`, `collector/justfile`, root `justfile`, `symbology-compose.yaml` |
| New Go files | ~14 | `api/` scaffold |
