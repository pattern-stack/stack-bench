# GCP Cloud SQL Variables

variable "environment" {
  description = "Deployment environment (staging, prod)"
  type        = string
}

variable "project" {
  description = "Project name"
  type        = string
}

variable "name" {
  description = "Database instance name (used for resource naming)"
  type        = string
}

variable "postgres_version" {
  description = "PostgreSQL version (e.g., 15, 14, 13)"
  type        = string
  default     = "15"
}

variable "size" {
  description = "Instance size tier (micro, small, medium, large, xlarge)"
  type        = string
  default     = "small"

  validation {
    condition     = contains(["micro", "small", "medium", "large", "xlarge"], var.size)
    error_message = "Size must be one of: micro, small, medium, large, xlarge."
  }
}

variable "region" {
  description = "GCP region"
  type        = string
}

variable "vpc_id" {
  description = "VPC network self_link for private IP connectivity"
  type        = string
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
  description = "Docker image for running migrations (leave empty to skip migration job)"
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
  description = "VPC Access Connector ID for Cloud Run to Cloud SQL connectivity"
  type        = string
  default     = null
}
