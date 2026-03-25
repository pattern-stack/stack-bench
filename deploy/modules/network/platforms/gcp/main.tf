# GCP Network Module
# Creates VPC Access Connector for Cloud Run to reach private resources

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

variable "project" {
  description = "GCP project ID"
  type        = string
}

variable "environment" {
  description = "Deployment environment"
  type        = string
}

variable "vpc_name" {
  description = "VPC network name"
  type        = string
  default     = "default"
}

variable "region" {
  description = "GCP region"
  type        = string
}

# VPC Access Connector - allows Cloud Run to reach private IPs in VPC
resource "google_vpc_access_connector" "main" {
  name          = "${var.project}-${var.environment}-connector"
  region        = var.region
  network       = var.vpc_name
  ip_cidr_range = "10.8.0.0/28"  # Dedicated /28 range for connector

  # Throughput settings (Mbps)
  min_throughput = 200
  max_throughput = 300
}

# Outputs
output "id" {
  description = "VPC network self link"
  value       = "projects/${var.project}/global/networks/${var.vpc_name}"
}

output "vpc_connector_id" {
  description = "VPC Access Connector ID for Cloud Run"
  value       = google_vpc_access_connector.main.id
}

output "vpc_connector_name" {
  description = "VPC Access Connector name"
  value       = google_vpc_access_connector.main.name
}
