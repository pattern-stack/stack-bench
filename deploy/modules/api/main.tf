# API Module
# Platform-specific API deployment (Cloud Run, LXC container, etc.)

locals {
  # Size tier mappings for CPU and memory
  size_configs = {
    micro  = { cpu = "0.25", memory = "256Mi" }
    small  = { cpu = "0.5",  memory = "512Mi" }
    medium = { cpu = "1",    memory = "1Gi" }
    large  = { cpu = "2",    memory = "2Gi" }
    xlarge = { cpu = "4",    memory = "4Gi" }
  }

  cpu    = local.size_configs[var.size].cpu
  memory = local.size_configs[var.size].memory
}

# GCP Cloud Run
module "gcp" {
  count  = var.platform == "gcp" ? 1 : 0
  source = "./platforms/gcp"

  name        = var.name
  environment = var.environment
  region      = var.region
  image       = var.image
  port        = var.port

  cpu    = local.cpu
  memory = local.memory

  min_instances = var.min_instances
  max_instances = var.max_instances

  database_url = var.database_url
  redis_url    = var.redis_url

  public = var.public

  health_path           = var.health_path
  startup_timeout       = var.startup_timeout
  startup_initial_delay = var.startup_initial_delay
  liveness_interval     = var.liveness_interval
  liveness_timeout      = var.liveness_timeout

  extra_env     = var.extra_env
  extra_secrets = var.extra_secrets

  vpc_connector_id = var.vpc_connector_id
}

# Outputs - route to correct platform
output "url" {
  description = "Public URL of the API service"
  value = module.gcp[0].url
}

output "internal_url" {
  description = "Internal URL of the API service"
  value       = "http://${var.name}:${var.port}"
}

output "revision" {
  description = "Current deployment revision"
  value       = var.platform == "gcp" ? module.gcp[0].revision : ""
}

output "service_name" {
  description = "Name of the deployed service"
  value       = var.name
}
