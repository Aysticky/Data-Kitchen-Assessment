# AGENTS.md

Fast orientation for AI coding assistants (and humans in a hurry). This file is allowed to go out of date — treat it as a map, not a contract.

## What this repo is

A reduced version of the DataKitchen engine. It parses YAML model configs, deploys Databricks Unity Catalog resources via Terraform, and runs Delta Lake loads on top of Spark.

The top-level `models/` directory stands in for a domain team's model YAMLs — the *consumer* side of the platform. `src/engine/` is the engine code — the side the candidate is extending.

> In the real DataKitchen, each model is a **SQL + YAML pair** (SQL selects source rows, YAML declares target schema and load mode). We've dropped the SQL side here — the assessment is about load modes, which operate on a DataFrame the engine hands in. Don't generate or expect `.sql` files.

The candidate's task is described in [README.md](README.md). This file describes **the code**, not the task.

## The engine pipeline

```
YAML config ──► ModelConfig (Pydantic) ──► Load execution (Delta)
                       │
                       └─► Terraform deployment (schema + tables)
```

Every load mode must plug into all three points:

1. A value on `LoadMode` in [`src/engine/config/enums.py`](src/engine/config/enums.py).
2. Configuration schema on `ModelConfig` in [`src/engine/config/model.py`](src/engine/config/model.py), including any validation rules specific to the mode.
3. A `Loader` implementation in [`src/engine/load/`](src/engine/load/) that runs against a Delta table.
4. Terraform needs to know which mode a table uses so operators can find it in deployment metadata; see [`terraform/main.tf`](terraform/main.tf).

## Existing load modes

| Mode | Semantics |
|------|-----------|
| `full` | Truncate and rewrite the target from the source DataFrame. |
| `full_compare` | Delta `MERGE`: insert new rows, update changed rows, physically delete rows absent from source. Requires primary keys. |

Both have tests in [`tests/test_load.py`](tests/test_load.py).

## Conventions

- **Python 3.11**, line length 88, ruff + mypy enforced (config in `pyproject.toml`).
- **Config models**: Pydantic v2 via `ConfigBaseModel`. The config changes needed for this assessment are intentionally small — a new enum value and one validation rule. Extend what's already there; don't invent new patterns.
- **Custom errors** live in [`src/engine/errors.py`](src/engine/errors.py). Raising a `ConfigError` (with `source=`) is preferred; plain `ValueError` is fine. Don't over-invest in the error layer.
- **Tests**: pytest. Spark-backed tests use the `spark` fixture in `conftest.py`. Delta tables live under `tmp_path`.
- **Docstrings**: Google style. Not required on every private helper, but public engine surface should have them.
- **Imports**: absolute from `engine.*` (the package is installed by `uv sync`, so no `src.` prefix).

## What is deliberately *not* here

- No real Databricks connectivity. Terraform uses the Databricks provider but CI runs only `terraform validate` + `fmt`.
- No real CI secrets. `deploy.yaml` is illustrative.
- No streaming, no change data feed, no cluster management, no scheduling, no observability. The real engine has all of these; the assessment doesn't need them.

## Commands

```bash
uv sync --all-extras                    # install
uv run pytest                           # tests
uv run pytest -k load                   # subset
uv run ruff check . && uv run ruff format --check .
uv run mypy src
```

## Where to put things

- New load mode logic → new file in `src/engine/load/`, exported from `src/engine/load/__init__.py`.
- New config fields → `src/engine/config/model.py`; new enum values → `src/engine/config/enums.py`.
- New Terraform outputs or table metadata → `terraform/main.tf` + `terraform/outputs.tf`.
- New error types → `src/engine/errors.py`.

If a change crosses several of these, that's expected.
