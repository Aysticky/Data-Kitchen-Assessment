# DK-812 — Deletion-Preserving Load Mode

## Design

**Load mode name**: `full_compare_soft_delete`

**YAML interface**: Domain teams configure will it in a similar way to `full_compare` to simply change the mode value in their model YAML:

```yaml
refresh:
  mode: full_compare_soft_delete
columns:
  - name: customer_id
    primary_key: true
    # ... other columns declared normally
```

**Deletion marker**: Engine-injected column `deleted_at` (timestamp, nullable).

Domain teams **would not declare** this column in their YAML. The engine adds it automatically to:
- The table schema deployed through Terraform (see `terraform/main.tf`)
- The target dataFrame during merge operations (see `full_compare_soft_delete.py`)

**Why this approach?**

1. **Separation of concerns**: `deleted_at` is engine metadata, not domain data. Domain teams shouldn't have to remember to add it or worry about its type/nullability.
2. **Consistency**: All soft-delete tables have the same deletion marker column, making cross-table queries and observability easier.
3. **Safety**: Domain teams can't accidentally misconfigure the deletion marker (wrong type, wrong name, non-nullable, etc.).
4. **Migration path**: Existing `full_compare` tables can switch to soft-delete mode by changing one line in YAML. No schema changes required in the YAML itself.

**Alternative considered and rejected**: Requiring domain teams to declare `deleted_at` in their YAML. This is more explicit but violates the (YAML only, no engine changes per domain) requirement, because teams would need to coordinate schema changes with the engine team to use the feature.

## Trade-offs

**What I deliberately did not do:**

1. **Configurable column name**: The deletion marker is always `deleted_at`. Supporting custom names (e.g, `is_active`, `tombstone_ts`) adds complexity without clear value. Standardization is better for observability and cross-team consistency.

2. **Soft-delete filtering in reads**: The engine doesn't automatically filter out soft-deleted rows when domain teams query their tables. Consumers must add `WHERE deleted_at IS NULL` if they only want active rows. This is intentional because:
   - Audit teams need to see deleted rows
   - Some use cases want historical state
   - Filtering can be added later through views if needed

3. **Retention policies**: Rows stay soft-deleted indefinitely. No auto-purge after N days. This keeps the implementation simple and meets the audit requirement. If storage becomes a concern, I can add retention configuration in a future sprint.

4. **Multi-column deletion state**: I store only a timestamp, not WHO deleted it or WHY. This keeps the schema additions minimal. If needed, I can extend to include `deleted_by` or `deletion_reason` fields.

**When I would revisit:**

- **Column name configurability**: If I get requests from multiple teams wanting different conventions (e.g, regulatory requirements for specific naming).
- **Auto-filtering**: If domain teams frequently forget to filter deleted rows and accidentally include them in downstream aggregations. I can add a view layer or a `include_deleted=false` query option.
- **Retention policies**: When storage costs or compliance requirements force us to physically purge old deletions.

## Risk

**Most fragile parts:**

1. **Schema evolution during first load**: The `_ensure_target_schema` method uses a try/except with a broad `except Exception` clause. If the Delta table exists but has schema issues unrelated to `deleted_at`, this could mask those errors. 
   - **Hardening**: Catch specific exceptions (for example, `AnalysisException` for missing table Vs schema mismatch). I can add explicit validation that the table exists before attempting ALTER TABLE.

2. **Terraform and runtime schema sync**: The Terraform template injects `deleted_at` into the deployed schema, but the loader also tries to add it at runtime. If Terraform changes are deployed but old code is still running, or vice versa, threre could be mismatches.
   - **Hardening**: I would add a schema validation step at load time that verifies `deleted_at` exists with the correct type before proceeding. Fail fast with a clear error message if the schema is unexpected.

3. **Race conditions on concurrent deletes**: If two loads run simultaneously with different source data, the `deleted_at` timestamp might vary between them. Delta's optimistic concurrency control handles write conflicts, but the final state might depend on execution order.
   - **Hardening**: Document that soft-delete loads should not run concurrently for the same table. I would add runtime locking or idempotency checks if we need to support concurrent loads.

4. **NULL handling in primary keys**: If source data has NULL values in primary key columns, the merge condition might behave unexpectedly (SQL NULL semantics: `NULL = NULL` is FALSE).
   - **Hardening**: I would add validation at config time to prohibit nullable primary keys. Or add runtime checks to reject source dataframes with NULL keys.

5. **Timestamp precision**: Using `current_timestamp()` for deletions. If the system clock is wrong or loads happen in rapid succession, timestamps might not reflect true deletion order.
   - **Hardening**: I would use a monotonic sequence number instead of timestamps, or use the Delta table version/transaction ID as the deletion marker. This would require rethinking the column type (bigint instead of timestamp).

## Follow-ups

**What to tackle in next sprint:**

1. **Add integration test with a real model YAML**: Currently tests use inline dataframes. I would add a test that loads a YAML config with `full_compare_soft_delete` mode, validates it, and runs the full load cycle end-to-end.

2. **Documentation for domain teams**: I would add a guide to the docs explaining:
   - When to use soft-delete Vs hard-delete (`full_compare`)
   - How to query active-only rows (`WHERE deleted_at IS NULL`)
   - How to audit deletions (query `deleted_at IS NOT NULL`)
   - Migration steps from `full_compare` to `full_compare_soft_delete`

3. **Observability metrics**: I would emit metrics on soft-delete operations for:
   - Number of rows soft-deleted per load
   - Number of rows restored per load
   - Table-level stats (active rows, deleted rows, oldest deletion timestamp)
   - These would help teams detect unexpected deletion patterns (e.g, mass deletion due to upstream data issues)

4. **Terraform validation**: I would add a `terraform plan` test that verifies the `deleted_at` column is correctly injected for soft-delete tables and not present for other modes.

5. **Config validation test**: I would add a test case in `test_config.py` that verifies `full_compare_soft_delete` mode fails validation if no primary keys are declared.

6. **Performance testing**: Soft-delete tables will grow unbounded unless purged. I would test query performance on tables with millions of deleted rows to understand when we need partitioning or retention policies.

## Bonus — `deploy.yaml` bug

**The bug**: The `apply` job does not use the Terraform plan generated in the `plan` job. It instead re-runs `terraform plan` implicitly during the `terraform apply` step.

```yaml
- name: Terraform apply
  run: |
    terraform apply -auto-approve \
      -var="environment=..." \
      -var="catalog_name=..." 
```

This creates a new plan at apply time with the current state of the workspace, not the plan that was reviewed in the previous job.

**Production impact**:

1. **Plan drift**: If someone push changes to `main` between the `plan` and `apply` jobs, the reviewed plan is not what gets applied. Reviewers approved plan A, but production gets plan B.

2. **Silent failures**: If the apply job uses different variable values or the model YAML files have changed, Terraform will silently create a different deployment than what was reviewed.

3. **Audit trail broken**: The plan artifact uploaded in the `plan` job is never used, so there's no guarantee that the reviewed plan matches what was deployed.

4. **Compliance risk**: For regulated environments, you must be able to prove that deployed changes match approved changes. This workflow can't make that guarantee.

**The solution**:

The `apply` job should download and apply the exact plan artifact created by the `plan` job:

```yaml
  apply:
    needs: [validate-config, plan]
    runs-on: ubuntu-latest
    environment: ${{ needs.validate-config.outputs.environment }}
    steps:
      - name: Download plan
        uses: actions/download-artifact@v4
        with:
          name: tfplan
          path: terraform/

      - name: Terraform apply
        if: ${{ vars.ENABLE_REAL_DEPLOY == 'true' }}
        working-directory: terraform
        run: terraform apply -auto-approve tfplan
```

Key changes:
1. I added `actions/download-artifact@v4` step to retrieve the `tfplan` artifact
2. I changed `terraform apply` to use the plan file directly as `terraform apply -auto-approve tfplan`
3. I removed the `-var` arguments from apply (they are already put into the plan)

This ensures the exact plan that was generated (and could be reviewed/approved) is the one that gets applied to production.

**Additional observation**:

The workflow comment states "Runs on merges to main", but the actual trigger is:

```yaml
on:
  pull_request:
    branches: [main]
```

This means the deploy workflow runs on pull requests, not on merges to main. In a real deployment workflow, I would align the trigger with the intended release process. For production deploys, the trigger should typically be:

```yaml
on:
  push:
    branches: [main]
```

This ensures deployments happen after PR approval and merge, not during PR review.

## AI assistant usage

I used Copilot to modify enum, Pydantic models, and Terraform templates. I also used it to debug the sparksession error. I also used it for re-structuring this NOTES.md