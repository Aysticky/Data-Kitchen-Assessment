# Instructions

Logistics and submission checklist for the assessment. Read [`README.md`](README.md) first — the task, context, and setup instructions all live there. This file is a checklist for the mechanics of hosting, branching, and submitting.

---

## Before you start

- [ ] **Host the repo on GitHub.** We share this assessment by email (we can't host public repos in the org), so we need somewhere to review from.
  - Public is easiest. Private is fine too — add the reviewers named in the email as collaborators.
- [ ] **Leave `main` exactly as you received it.** No pushes, no force-pushes, no rebases onto `main`. We diff `main` vs. your branch.
- [ ] **Create one working branch** off `main` (e.g. `feat/dk-812-soft-delete`). Everything lives on that branch.
- [ ] Read [`README.md`](README.md). Skim [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) and [`AGENTS.md`](AGENTS.md).
- [ ] Get the environment running (README → *Setup*) and confirm `uv run pytest` is green before you change anything.

## While you work

- [ ] **All changes land in one PR** from your branch → `main`. Open it early (draft is fine), push commits to it as you go.
- [ ] Use the existing `full` and `full_compare` implementations as your style reference.
- [ ] When the brief is ambiguous, **make a call and flag it** — a `# ASSUMED:` comment or a bullet in `NOTES.md`. Don't block on us.

## Before you submit

- [ ] **CI is green on your PR.** Lint, type-checks, tests, and `terraform validate`/`fmt` run automatically on every push to the PR.
- [ ] `NOTES.md` (or the PR description) covers **Design / Trade-offs / Risk / Follow-ups** — see README → *Submission*.
- [ ] If you used an AI assistant, mention it in the write-up. Expected, not penalised.
- [ ] Mark the PR **Ready for review** and reply to the email with the link.

---

## What to skip if time is tight

- Exhaustive test coverage — a handful of tests that defend design decisions beats a full matrix.
- Polishing code that isn't on the critical path for your new mode.
- CI workflow changes beyond the bonus bug.

## If something is broken on our side

If a test fails on a clean clone or a dependency won't resolve, reply to the email — that's our bug, not the assessment.
