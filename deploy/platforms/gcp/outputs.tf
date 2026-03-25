# Deployment Outputs

output "backend_url" {
  description = "Backend API URL"
  value       = module.backend.url
}

output "frontend_url" {
  description = "Frontend URL"
  value       = module.frontend.url
}

output "database_connection" {
  description = "Database connection string"
  value       = module.database.connection_string
  sensitive   = true
}

# GCP Console URLs for quick access
output "console_urls" {
  description = "Direct links to GCP Console resources"
  value = {
    cloud_run_backend = "https://console.cloud.google.com/run/detail/${var.region}/stack-bench-backend?project=${var.project_id}"
    cloud_run_frontend = "https://console.cloud.google.com/run/detail/${var.region}/stack-bench-frontend?project=${var.project_id}"
    cloud_sql = "https://console.cloud.google.com/sql/instances/stack-bench-${var.environment}-db?project=${var.project_id}"
    vpc_connector = "https://console.cloud.google.com/networking/connectors?project=${var.project_id}"
    secret_manager = "https://console.cloud.google.com/security/secret-manager?project=${var.project_id}"
  }
}
