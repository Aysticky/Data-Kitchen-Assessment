# Unity Catalog schema + tables for a single engine-managed dataset.
#
# Tables are discovered by reading the model YAML files under ../models
# directly, so the YAML is the single source of truth: add or change a
# model YAML and Terraform picks it up on the next plan.

locals {
  model_files = fileset("${path.module}/../models", "*.yaml")

  decoded_models = [
    for f in local.model_files : yamldecode(file("${path.module}/../models/${f}"))
  ]

  table_configs = {
    for m in local.decoded_models : m.name => {
      load_mode = m.refresh.mode
      comment   = try(m.description, "")
      columns = [
        for c in m.columns : {
          name      = c.name
          data_type = c.data_type
          nullable  = try(c.nullable, true)
        }
      ]
    }
  }
}

resource "databricks_schema" "this" {
  catalog_name = var.catalog_name
  name         = var.schema_name
  owner        = var.owner_group
  comment      = "Managed by the DataKitchen engine (${var.environment})."

  lifecycle {
    prevent_destroy = true
  }
}

resource "databricks_sql_table" "tables" {
  for_each = local.table_configs

  catalog_name = var.catalog_name
  schema_name  = databricks_schema.this.name
  name         = each.key
  table_type   = "EXTERNAL"

  comment = trimspace(
    "${each.value.comment}\n[load_mode=${each.value.load_mode}]"
  )

  dynamic "column" {
    for_each = each.value.columns
    content {
      name     = column.value.name
      type     = column.value.data_type
      nullable = column.value.nullable
    }
  }
}
