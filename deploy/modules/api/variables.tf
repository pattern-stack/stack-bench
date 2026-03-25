# API Module Variables
# Platform-agnostic interface for API deployment

variable "platform" {
  description = "Target platform (gcp, proxmox)"
  type        = string
}

variable "environment" {
  description = "Deployment environment (staging, prod)"
  type        = string
}

variable "name" {
  description = "Service name"
  type        = string
}

variable "runtime" {
  description = "Application runtime (python, node, etc.)"
  type        = string
  default     = "python"
}

variable "port" {
  description = "Container port"
  type        = number
  default     = 8000
}

variable "image" {
  description = "Container image URL with tag"
  type        = string
}

variable "size" {
  description = "Size tier (micro, small, medium, large, xlarge)"
  type        = string
  default     = "small"

  validation {
    condition     = contains(["micro", "small", "medium", "large", "xlarge"], var.size)
    error_message = "Size must be one of: micro, small, medium, large, xlarge."
  }
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

variable "network_id" {
  description = "Network identifier"
  type        = string
}

variable "region" {
  description = "Deployment region"
  type        = string
  default     = null
}

variable "public" {
  description = "Allow public (unauthenticated) access"
  type        = bool
  default     = true
}

variable "min_instances" {
  description = "Minimum instance count (0 = scale to zero)"
  type        = number
  default     = 0
}

variable "max_instances" {
  description = "Maximum instance count"
  type        = number
  default     = 10
}

variable "health_path" {
  description = "Health check endpoint path"
  type        = string
  default     = "/health"
}

variable "startup_timeout" {
  description = "Startup probe timeout in seconds"
  type        = number
  default     = 30
}

variable "startup_initial_delay" {
  description = "Startup probe initial delay in seconds"
  type        = number
  default     = 10
}

variable "liveness_interval" {
  description = "Liveness probe interval in seconds"
  type        = number
  default     = 30
}

variable "liveness_timeout" {
  description = "Liveness probe timeout in seconds"
  type        = number
  default     = 10
}

variable "extra_env" {
  description = "Additional environment variables"
  type        = map(string)
  default     = {}
}

variable "extra_secrets" {
  description = "Additional secrets from Secret Manager (name -> secret_id)"
  type        = map(string)
  default     = {}
}

variable "vpc_connector_id" {
  description = "VPC Access Connector ID for private network access (GCP)"
  type        = string
  default     = null
}
