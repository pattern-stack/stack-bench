# GCP Platform Configuration
# Project: stack-bench

# Network Module
module "network" {
  source = "../../modules/network"

  platform    = "gcp"
  environment = var.environment
  project     = var.project_id
  vpc_name    = var.vpc_name
  region      = var.region
}

# Database Module
module "database" {
  source = "../../modules/database"

  platform    = "gcp"
  environment = var.environment
  project     = "stack-bench"
  name        = "stack-bench-db"
  engine           = "postgres"
  postgres_version = "15"
  size        = var.environment == "prod" ? "small" : "micro"

  network_id  = module.network.id
  region      = var.region
}

# Backend API Module
module "backend" {
  source = "../../modules/api"

  platform    = "gcp"
  environment = var.environment
  name        = "stack-bench-backend"
  runtime     = "python"
  port        = 8000
  image       = "${var.registry_url}/backend:${var.image_tag}"

  size        = var.environment == "prod" ? "medium" : "small"

  # Scaling
  min_instances = var.environment == "prod" ? 1 : 0
  max_instances = var.environment == "prod" ? 10 : 1

  # Health checks
  health_path           = "/health"
  startup_initial_delay = 10
  startup_timeout       = 5
  liveness_interval     = 10
  liveness_timeout      = 5

  # Connections
  database_url = module.database.connection_string

  network_id   = module.network.id
  region           = var.region
  vpc_connector_id = module.network.vpc_connector_id
}

# Frontend Module
module "frontend" {
  source = "../../modules/static"

  platform    = "gcp"
  environment = var.environment
  name        = "stack-bench-frontend"
  image       = "${var.registry_url}/frontend:${var.image_tag}"

  enable_cdn  = var.environment == "prod"

  network_id  = module.network.id
  region      = var.region
}
