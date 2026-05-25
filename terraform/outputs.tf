output "schema_id" {
  description = "Full identifier of the managed schema."
  value       = databricks_schema.this.id
}

output "table_ids" {
  description = "Map of table name to Databricks table identifier."
  value       = { for name, tbl in databricks_sql_table.tables : name => tbl.id }
}

output "load_modes" {
  description = "Map of table name to declared load mode (for operator discovery)."
  value       = { for name, cfg in local.table_configs : name => cfg.load_mode }
}
