# DataKitchen Engine — Software / Platform Engineer Take-Home

Welcome. This assessment simulates your **first sprint on the DataKitchen engine team**.

> **Logistics:** before you start and before you submit, follow the checklist in [`INSTRUCTIONS.md`](INSTRUCTIONS.md). It covers hosting, branch rules, and the submission steps.

DataKitchen is a config-driven data platform framework that runs on Databricks. Domain teams (customer, merchandising, supply chain, etc.) describe their tables and pipelines in SQL and YAML, and the engine validates the configuration, deploys the infrastructure, and processes the data. **You're joining the team that builds and maintains the engine itself** — not a team that uses it.

The engine in this repo is a deliberately small slice of the real one. It already supports two load modes (`full` and `full_compare`) end-to-end: schema validation, Delta merge logic, Terraform deployment, and CI. Your job is to add a new capability that domain teams have asked for, make it safe to adopt, and make it operable.

---

## The Ticket

> **DK-812 — Add a deletion-preserving load mode**
>
> Several domain teams run `full_compare` on audit-sensitive tables (customers, orders, stock positions). `full_compare` physically deletes rows that disappear from the source system, and the governance team has flagged this: auditors need to see *when* a record was removed and reason about historical state.
>
> Extend the engine so model authors can opt into **deletion-preserving** behaviour via configuration. The required data invariants are:
>
> - A row that disappears from source must be **retained** in the target and marked inactive with a timestamp recording when it was first seen as absent.
> - A row that reappears in source must be **restored to active** — the deletion timestamp cleared and the row updated as normal.
> - Both operations must be **idempotent**: running the load again with the same source produces the same target state.
>
> How you represent the deletion marker (column name, schema shape, whether it is declared by the domain team or injected by the engine) is a design decision — make a call and explain it in `NOTES.md`.
>
> This needs to work end-to-end:
>
> 1. Model authors configure it with **YAML only** — no engine changes per domain.
> 2. **Invalid configurations fail at validation time** with an error that tells the domain engineer what is wrong and where.
> 3. **Operators can tell which tables use it** from deployment metadata, without reading every YAML file.
> 4. The **data behaviour** is correct across inserts, updates, soft deletes, and the reappearance case.

That's the whole brief. How you implement it is up to you.

---

## What's Already Here

```
.
├── .github/workflows/            ci + deploy workflows
├── docs/ARCHITECTURE.md          platform context
├── models/                       stands in for a domain team's model YAMLs
├── src/engine/
│   ├── config/                   Pydantic schema + YAML loader (engine-side)
│   ├── load/                     full + full_compare load implementations
│   └── errors.py                 engine error types (intentionally minimal)
├── terraform/                    schema + table resources for the existing modes
└── tests/                        reference tests for the existing modes
├── AGENTS.md                     quick orientation (AI-friendly)
```

In the real platform **`models/` is domain-owned** — the SQL and YAML a domain team would usually commit to their own repo but included here for simplicity.

**`src/engine/` is platform-owned** — what your team ships. It is packaged as a Python wheel, deployed to Databricks via CI/CD, and executed there. A domain team should never need to change engine code to ship a new table; they change their model files only. That boundary is what the brief's "YAML only" requirement is protecting. See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full deployment chain.

> In the real platform each model is a **SQL + YAML pair** — SQL selects the source rows, YAML declares the target schema, load mode, and other metadata. We've dropped the SQL side for this assessment: the ticket is about load modes, which operate on a DataFrame the engine hands in. How that DataFrame is built isn't in scope.

The config changes needed for the new mode are deliberately small — a new enum value and one validation rule. Getting the runtime behaviour right is where the work is.

`full` and `full_compare` are fully implemented and tested. Treat them as the reference for style, structure, and the kinds of concerns the engine cares about. You are welcome (and expected) to refactor shared code if your new capability reveals a better shape.

---

## Scope

You should aim for **roughly 3 hours**. The expectation is not that you produce something polished to production standards in that window — it's that you exercise judgement about where to spend time.

The assessment rewards, roughly in priority order:

1. Getting the **data behaviour** right — inserts, updates, soft deletes, and the reappearance case. This is where most of the signal is.
2. Tests that **justify your design choices** — four focused scenarios beat twenty shallow ones.
3. **Deployment pipeline** awareness — pay attention to the full deploy workflow end-to-end.
4. A **configuration surface** that a domain engineer can read without knowing engine internals.

It does not reward:

- Pydantic framework expertise — the config layer is thin scaffolding, not a design exercise.
- Terraform module design — recording the new mode in deployment metadata is all that's needed.
- Guessing what we want — if something is underspecified, make a call, do it, and tell us why.

If you run short on time, it is fine (and expected) to leave TODO comments or skipped tests calling out what you'd do next. We care more about how you think than about how much you produce.

## Bonus

There is a bug in `deploy.yaml` that would allow production to silently diverge from the plan that was reviewed. If you spot it, fix it and explain the production impact in `NOTES.md`.

---

## Submission

When you're done, include a short write-up in the body of the `NOTES.md` file, or as a PR description, or other. Keep it to roughly a page. Cover:

1. **Design** — what interface did you expose to domain teams, and why?
2. **Trade-offs** — what did you deliberately *not* do, and under what conditions would you revisit it?
3. **Risk** — where is your implementation most fragile, and how would you harden it?
4. **Follow-ups** — what would you tackle in the next sprint?

We'll use this as the starting point for the follow-up conversation.

---

## Setup

### Option A — Local with `uv` (recommended)

[`uv`](https://docs.astral.sh/uv/) handles the virtualenv, the interpreter, and the dependencies.

```bash
uv sync --all-extras
uv run pytest
uv run ruff check .
uv run mypy src
```

You will need Java 17 on your PATH for PySpark. On macOS: `brew install openjdk@17`. On Linux: `apt install openjdk-17-jdk`. On Windows: [Temurin](https://adoptium.net/).

### Option B — Docker

If you'd rather not install Java locally:

```bash
docker build -t dk-assessment .
docker run --rm -it -v "${PWD}:/workspace" dk-assessment
# inside the container:
uv run pytest
uv run ruff check .
uv run mypy src
```

Terraform is not required to be installed; we only ever run `terraform validate` and `terraform fmt` in CI, and you can do the same locally if you have it.

---

## Uncertain about something?

If the brief feels ambiguous, **make your best guess and flag it** — either with a comment in the code (`# ASSUMED: ...`) or a short bullet in `NOTES.md`. Surfacing the assumption is what matters; we'd rather see a defended choice than a question you couldn't ask.
