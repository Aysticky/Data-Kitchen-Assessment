# Architecture

Platform context for the assessment. This explains *why* the engine is shaped the way it is — the concepts and deployment model you need to reason about the ticket. For the code map and file-level conventions, see [`AGENTS.md`](../AGENTS.md). For the task brief, see [`README.md`](../README.md).

## Mental model

The engine is a **compiler + runtime** for declarative data pipelines:

- **Compile time** — model configs are parsed into Pydantic models, validated, and used to generate Terraform resources (schemas, tables, metadata).
- **Run time** — the engine loads source data into a target Delta table using the load mode declared in the config.

In the real platform each model is a **SQL + YAML pair**: SQL selects the source rows, YAML declares the target schema, load mode, and other metadata. Domain teams author both; everything else — validation, Terraform, Delta merge semantics, operational metadata — is the platform's responsibility. We've dropped the SQL side for this assessment because the ticket is about load modes, which operate on a DataFrame the engine hands in.

## How a model flows through the system

```
model.sql + model.yaml ──► ModelConfig (Pydantic) ──► Validation
(SQL builds the source DataFrame; YAML declares schema + load mode)
                       │                        │
                       │                   fail fast with
                       │                   actionable errors
                       │
                       ├──► Terraform ──► Unity Catalog schema + tables
                       │                  (metadata: load mode, tags, properties)
                       │
                       └──► Loader.run() ──► Delta table writes
```

A new load mode must plug into all three stages: **config schema**, **Terraform metadata**, and **load execution**. Each load mode is a class that implements `Loader.run(source_df, target_table_path)`. Modes that need primary keys declare that requirement through validation; modes that don't, don't. The existing `full` and `full_compare` modes demonstrate the full pattern.

## How it reaches Databricks

The engine is packaged as a **Python wheel**. Domain teams never run it locally — it is deployed and executed on Databricks clusters. The deployment chain:

1. Domain team merges a model change to their repo.
2. CI/CD pipeline validates config, uploads the engine wheel + models to the workspace, and runs Terraform to deploy schemas/tables.
3. The engine wheel runs on Databricks against the deployed Delta tables.

All deployments go through the CI/CD pipeline — there is no manual path to production. Two workflows in this repo mirror the real pipeline:

- `ci.yaml` — runs on PRs: lint, type-check, unit tests, `terraform validate`, `terraform fmt`.
- `deploy.yaml` — runs on merge to main: validates config, plans Terraform, then applies. In the real system these steps target Databricks workspaces via OIDC.

Treat `deploy.yaml` as a production pipeline, not scaffolding — the bonus bug is a CI/CD concern that only matters if you take deployment seriously.

## Terraform as the metadata surface

The `terraform/` directory provisions Unity Catalog **schemas** and **tables**. Table configuration is read directly from the model YAML files via `fileset` + `yamldecode`, so the YAML is the single source of truth: add or change a model YAML and Terraform picks it up on the next plan.

Operationally, the team needs to know which tables use which load mode without reading every YAML file. Terraform is where that metadata surfaces — through table properties, tags, or comments.

## Validation philosophy

An invalid config should fail at the earliest possible stage, with a message that tells the domain engineer *what is wrong and where*. "Invalid config" is not acceptable; "Column `order_id` in `orders_raw.yaml` has primary-key constraint but load mode `full` does not use primary keys" is.

The current error layer is minimal and does not fully live up to this. Improving it is in scope for the assessment but not a core focus.
