# GCP Cloud Run API Variables

variable "name" {
  description = "Service name"
  type        = string
}

variable "environment" {
  description = "Deployment environment"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
}

variable "image" {
  description = "Container image URL"
  type        = string
}

variable "port" {
  description = "Container port"
  type        = number
  default     = 8000
}

variable "cpu" {
  description = "CPU limit (e.g., '1', '2', '0.5')"
  type        = string
  default     = "1"
}

variable "memory" {
  description = "Memory limit (e.g., '512Mi', '1Gi')"
  type        = string
  default     = "512Mi"
}

variable "min_instances" {
  description = "Minimum instance count"
  type        = number
  default     = 0
}

variable "max_instances" {
  description = "Maximum instance count"
  type        = number
  default     = 10
}

variable "database_url" {
  description = "Database connection string"
  type        = string
  default     = ""
  sensitive   = true
}

variable "redis_url" {
  description = "Redis connection string"
  type        = string
  default     = ""
  sensitive   = true
}

variable "public" {
  description = "Allow public access"
  type        = bool
  default     = true
}

variable "health_path" {
  description = "Health check path"
  type        = string
  default     = "/health"
}

variable "startup_timeout" {
  description = "Startup probe timeout"
  type        = number
  default     = 30
}

variable "startup_initial_delay" {
  description = "Startup probe initial delay"
  type        = number
  default     = 10
}

variable "liveness_interval" {
  description = "Liveness probe interval"
  type        = number
  default     = 30
}

variable "liveness_timeout" {
  description = "Liveness probe timeout"
  type        = number
  default     = 10
}

variable "extra_env" {
  description = "Additional environment variables"
  type        = map(string)
  default     = {}
}

variable "extra_secrets" {
  description = "Secrets from Secret Manager"
  type        = map(string)
  default     = {}
}

variable "vpc_connector_id" {
  description = "VPC Access Connector ID for private network connectivity"
  type        = string
  default     = null
}
