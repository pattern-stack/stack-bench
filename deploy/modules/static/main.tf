# Static/Frontend Module
# Platform-specific static site deployment (Cloud Storage+CDN, LXC nginx, etc.)

variable "platform" {
  type = string
}

variable "environment" {
  type = string
}

variable "name" {
  type = string
}

variable "image" {
  type = string
}

variable "enable_cdn" {
  type    = bool
  default = false
}

variable "network_id" {
  type = string
}

variable "region" {
  type    = string
  default = null
}

# Placeholder - implement platform-specific static hosting
output "url" {
  value = "https://${var.name}.example.com"
}

output "cdn_url" {
  value = var.enable_cdn ? "https://cdn.${var.name}.example.com" : null
}
