# Network Module
# Platform-specific network configuration including VPC Connector for serverless

variable "platform" {
  description = "Target platform (gcp, proxmox)"
  type        = string
}

variable "environment" {
  description = "Deployment environment (staging, prod)"
  type        = string
}

variable "project" {
  description = "Project name or GCP project ID"
  type        = string
}

variable "vpc_name" {
  description = "VPC network name"
  type        = string
  default     = "default"
}

variable "region" {
  description = "Cloud region"
  type        = string
  default     = null
}

variable "bridge" {
  description = "Proxmox network bridge"
  type        = string
  default     = "vmbr0"
}

variable "vlan" {
  description = "VLAN ID (Proxmox)"
  type        = number
  default     = null
}

# GCP Network with VPC Connector
module "gcp" {
  count  = var.platform == "gcp" ? 1 : 0
  source = "./platforms/gcp"

  project     = var.project
  environment = var.environment
  vpc_name    = var.vpc_name
  region      = var.region
}

# Unified outputs
output "id" {
  description = "Network/VPC identifier"
  value = module.gcp[0].id
}

output "vpc_connector_id" {
  description = "VPC Access Connector ID (GCP only, for Cloud Run)"
  value = var.platform == "gcp" ? module.gcp[0].vpc_connector_id : null
}
