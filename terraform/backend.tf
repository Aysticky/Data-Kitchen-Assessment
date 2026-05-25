terraform {
  # In production this would point at an Azure Storage or S3 remote
  # state configured per environment. For the assessment we use the
  # default local backend and rely on `terraform validate` + `fmt` in CI.
}
