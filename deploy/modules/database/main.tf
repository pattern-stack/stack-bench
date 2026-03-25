# Database Module
# Platform-specific database deployment (Cloud SQL, LXC postgres, etc.)

variable "platform" {
  description = "Target platform (gcp, proxmox)"
  type        = string
}

variable "environment" {
  description = "Deployment environment (staging, prod)"
  type        = string
}

variable "project" {
  description = "Project name"
  type        = string
  default     = ""
}

variable "name" {
  description = "Database instance name"
  type        = string
}

variable "engine" {
  description = "Database engine"
  type        = string
  default     = "postgres"
}

variable "postgres_version" {
  description = "PostgreSQL version (e.g., 15, 14)"
  type        = string
  default     = "15"
}

variable "size" {
  description = "Instance size tier (micro, small, medium, large, xlarge)"
  type        = string
  default     = "small"
}

variable "network_id" {
  description = "VPC network ID for private connectivity"
  type        = string
}

variable "region" {
  description = "Deployment region"
  type        = string
  default     = null
}

variable "database_name" {
  description = "Name of the database to create"
  type        = string
  default     = "app"
}

variable "database_user" {
  description = "Database user name"
  type        = string
  default     = "app"
}

variable "migration_image" {
  description = "Docker image for running migrations"
  type        = string
  default     = ""
}

variable "migration_timeout" {
  description = "Timeout for migration job in seconds"
  type        = number
  default     = 300
}

variable "backup_retention_days" {
  description = "Number of days to retain backups"
  type        = number
  default     = 7
}

variable "vpc_connector_id" {
  description = "VPC connector ID for serverless access (GCP)"
  type        = string
  default     = null
}

# Platform router - delegates to platform-specific implementation
module "gcp" {
  count  = var.platform == "gcp" ? 1 : 0
  source = "./platforms/gcp"

  environment           = var.environment
  project               = var.project != "" ? var.project : var.name
  name                  = var.name
  postgres_version      = var.postgres_version
  size                  = var.size
  region                = var.region
  vpc_id                = var.network_id
  database_name         = var.database_name
  database_user         = var.database_user
  migration_image       = var.migration_image
  migration_timeout     = var.migration_timeout
  backup_retention_days = var.backup_retention_days
  vpc_connector_id      = var.vpc_connector_id
}

# Unified outputs
output "connection_string" {
  description = "Database connection string"
  value = module.gcp[0].connection_string
  sensitive = true
}

output "host" {
  description = "Database host"
  value       = module.gcp[0].host
}

output "port" {
  description = "Database port"
  value       = 5432
}

output "instance_connection_name" {
  description = "Cloud SQL instance connection name (GCP only)"
  value       = var.platform == "gcp" ? module.gcp[0].instance_connection_name : null
}

output "migration_job_name" {
  description = "Migration job name (GCP only)"
  value       = var.platform == "gcp" ? module.gcp[0].migration_job_name : null
}
