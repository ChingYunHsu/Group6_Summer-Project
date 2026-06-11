# ClearPath Agent Guide

## Scope

These instructions apply to the `Group6_Summer-Project` repository.

- Treat `superpowers/` as a separate nested repository/submodule. Do not edit,
  reformat, or include it in project-wide scans unless the task explicitly
  targets that repository.
- More specific `AGENTS.md` files override this file inside their directory.
- Preserve unrelated user changes. Check `git status --short` before and after
  editing.

## Project Purpose

ClearPath is an accessibility intelligence application focused on Manhattan.
The repository currently contains:

- `src/`: Flask API prototype and mock responses.
- `openapi.yaml`: API contract under active development.
- `Data+ML/`: data analysis, database design, and ETL notebooks.
- `docker/mysql/init/`: schema used to initialize the Docker MySQL service.
- `docs/memory/`: durable project decisions, status, and handoff notes.
- `frontend/` and `backend/`: reserved implementation directories.

Do not describe placeholder directories or prototype modules as production
implementations.

## Read Before Editing

Read only the documents relevant to the requested area:

1. `README.md` for team workflow and architecture.
2. `docs/memory/project-overview.md` for the current project summary.
3. `docs/memory/pipeline-requirements.md` for sprint requirements.
4. `docs/memory/final-requirements-database-impact.md` for final-requirement
   database constraints.
5. `Data+ML/test/6.2-6.5_DB/README.md` before changing the database notebook.
6. `docs/memory/api-schema-gap-status.md` and
   `docs/memory/openapi-vs-schema-gap.md` when aligning API and schema.

Memory documents may become stale. Verify their claims against current source,
schema, notebook cells, and Git history before relying on them.

## Sources of Truth

Use the following ownership boundaries:

- Product and sprint behavior: current requirement documents in
  `docs/memory/`.
- HTTP paths and payloads: `openapi.yaml`.
- Docker bootstrap schema: `docker/mysql/init/001_clearpath_schema.sql`.
- ETL behavior and migrations:
  `Data+ML/test/6.2-6.5_DB/database_build.ipynb`.
- Notebook operating instructions:
  `Data+ML/test/6.2-6.5_DB/README.md`.

There are multiple `001_clearpath_schema.sql` files and they are not identical.
Do not copy one over another blindly. Identify the target environment, explain
the intended authority, and validate the resulting schema/API compatibility.

## Working Rules

- Keep changes scoped to the user request.
- Prefer existing naming, data models, and file structure over introducing a
  parallel abstraction.
- Do not add credentials, API keys, source datasets, generated databases, or
  notebook checkpoints to Git.
- Read configuration from environment variables. Do not introduce new
  hard-coded local absolute paths.
- When behavior changes, update the nearest README or relevant
  `docs/memory/` record in the same change.
- Record unresolved assumptions and validation limitations explicitly.
- Do not claim a full test or successful `Run All` unless it was actually
  performed.

## Database Safety

The local Docker services are defined in `docker-compose.yml`.

```bash
docker compose config
docker compose up -d mysql phpmyadmin
docker compose ps
```

MySQL is exposed on `127.0.0.1:3306`; phpMyAdmin is exposed on
`http://127.0.0.1:8080`.

- Never run `docker compose down -v`, delete the MySQL volume, drop tables, or
  execute the notebook schema-rebuild cell without explicit approval.
- Use an isolated test database or a verified backup/restore path for
  destructive schema tests.
- Treat migrations as idempotent operations. Distinguish already-applied
  objects from real SQL failures.
- Preserve transaction boundaries: commit a complete logical operation and
  roll back on database errors.
- Log the source dataset, stable record identifier, and failure reason for ETL
  errors.

The database notebook supports these environment variables:

- `CLEARPATH_PROJECT_ROOT`
- `CLEARPATH_DATA_ROOT`
- `CLEARPATH_DB_HOST`
- `CLEARPATH_DB_PORT`
- `CLEARPATH_DB_USER`
- `CLEARPATH_DB_PASSWORD`
- `CLEARPATH_DB_NAME`

Do not assume the external source datasets are stored in this Git repository.

## Notebook Rules

For `database_build.ipynb`:

- Preserve the logical order: initialization, validation, utility functions,
  schema/migrations, ETL, weather/language ETL, then final verification.
- Keep migration definitions and migration execution in their canonical cells;
  do not restore legacy migration paths.
- Reuse the shared ETL transaction helpers instead of adding per-row
  `commit/rollback` templates.
- Use specific exception types; avoid bare `except:`.
- Maintain deterministic IDs and document whether deduplication is
  within-source, cross-source, or database-key based.
- Preserve meaningful location features such as AED floor information.
- Clear outputs and execution counts before committing unless output is
  explicitly required as evidence.
- Update `Data+ML/test/6.2-6.5_DB/README.md` when cell roles or ordering change.

Minimum static notebook validation:

```bash
python - <<'PY'
import ast
import json
from pathlib import Path

path = Path("Data+ML/test/6.2-6.5_DB/database_build.ipynb")
notebook = json.loads(path.read_text(encoding="utf-8"))
for index, cell in enumerate(notebook["cells"]):
    if cell["cell_type"] == "code":
        ast.parse("".join(cell["source"]), filename=f"cell-{index}")
print(f"validated {len(notebook['cells'])} cells")
PY
```

If `nbformat` is installed, also run:

```bash
python - <<'PY'
from pathlib import Path

import nbformat

path = Path("Data+ML/test/6.2-6.5_DB/database_build.ipynb")
notebook = nbformat.read(path, as_version=4)
nbformat.validate(notebook)
print("nbformat validation passed")
PY
```

Run the full notebook only against an isolated database when destructive cells
are enabled. Verify both a clean run and a second idempotency run.

## Python API Rules

The code in `src/` is currently a prototype and has no repository-level
dependency manifest or automated test suite.

- Keep API behavior aligned with `openapi.yaml`.
- Avoid expanding mock-data behavior into an undocumented contract.
- Use Flask blueprints consistently with the existing modules.
- Add tests with new production behavior instead of relying only on manual
  endpoint checks.
- If dependencies are added, introduce and document one canonical dependency
  manifest rather than ad hoc installation commands.

Minimum source validation:

```bash
python - <<'PY'
import ast
from pathlib import Path

files = sorted(Path("src").rglob("*.py"))
for path in files:
    ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
print(f"validated {len(files)} Python files")
PY
```

This checks syntax only. It is not an integration test.

## Validation Checklist

Run the checks relevant to the files changed:

```bash
git status --short
docker compose config
```

Also run the Python AST validation above for changes under `src/`.

For schema or ETL changes, additionally verify:

- SQL parses and applies in an isolated MySQL 8.4 database.
- Migrations can run twice without unintended changes.
- Invalid input and SQL errors leave transactions in a valid state.
- A second ETL run does not create duplicate rows.
- API fields still map to the resulting schema.
- Notebook outputs and execution counts are cleared before commit.

If a check cannot run because dependencies, datasets, permissions, or an
isolated database are unavailable, report that limitation precisely.

## Durable Project Memory

Use `docs/memory/` as the shareable cross-session record:

- Update an existing topic file instead of creating overlapping notes.
- Add dated entries to `docs/memory/session-log.md` for substantial completed
  work, decisions, blockers, and pending follow-ups.
- Keep memory concise and factual; link to canonical source files rather than
  duplicating large code or schema blocks.
- Do not treat tool-specific conversation memory as a substitute for committed
  project documentation.

## Git Workflow

- Follow the branch and pull-request policy in `README.md`.
- Use one focused problem per commit or pull request.
- Do not amend, reset, force-push, or revert unrelated work unless explicitly
  requested.
- Before handing off, summarize changed files, checks run, checks not run, and
  remaining risks.
