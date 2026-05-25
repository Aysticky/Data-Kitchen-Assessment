variable "environment" {
  type        = string
  description = "Deployment environment."
  validation {
    condition     = contains(["nonprd", "preprd", "prd"], var.environment)
    error_message = "Environment must be one of: nonprd, preprd, prd."
  }
}

variable "catalog_name" {
  type        = string
  description = "Unity Catalog catalog name."
}

variable "schema_name" {
  type        = string
  description = "Schema name within the catalog."
}

variable "owner_group" {
  type        = string
  description = "AD group that owns the schema and its tables."
}
