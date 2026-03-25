# Cache Module
# Platform-specific cache deployment (Memorystore, LXC redis, etc.)

variable "platform" {
  type = string
}

variable "environment" {
  type = string
}

variable "name" {
  type = string
}

variable "engine" {
  type    = string
  default = "redis"
}

variable "redis_version" {
  type    = string
  default = "7"
}

variable "size" {
  type    = string
  default = "small"
}

variable "network_id" {
  type = string
}

variable "region" {
  type    = string
  default = null
}

# Placeholder - implement platform-specific cache
output "connection_string" {
  value     = "redis://${var.name}:6379"
  sensitive = true
}

output "host" {
  value = var.name
}

output "port" {
  value = 6379
}
