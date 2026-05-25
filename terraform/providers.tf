terraform {
  required_version = ">= 1.5"
  required_providers {
    databricks = {
      source  = "databricks/databricks"
      version = ">= 1.50"
    }
  }
}

provider "databricks" {
  # In CI this would be wired to the target workspace via OIDC.
  # For `terraform validate` no credentials are required.
  host = "https://example.cloud.databricks.com"
}
