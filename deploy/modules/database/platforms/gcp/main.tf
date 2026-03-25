# GCP Cloud SQL Database Module
# Provisions Cloud SQL PostgreSQL with Secret Manager and migration job

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}

# Size tier mapping
locals {
  size_tiers = {
    micro = {
      tier      = "db-f1-micro"
      disk_size = 10
    }
    small = {
      tier      = "db-g1-small"
      disk_size = 20
    }
    medium = {
      tier      = "db-n1-standard-1"
      disk_size = 50
    }
    large = {
      tier      = "db-n1-standard-2"
      disk_size = 100
    }
    xlarge = {
      tier      = "db-n1-standard-4"
      disk_size = 200
    }
  }

  selected_tier = local.size_tiers[var.size]

  # Build connection string for Cloud SQL socket connection
  database_url = "postgresql://${google_sql_user.main.name}:${random_password.db_password.result}@/${google_sql_database.main.name}?host=/cloudsql/${google_sql_database_instance.main.connection_name}"
}

# Cloud SQL Instance
resource "google_sql_database_instance" "main" {
  name             = "${var.project}-${var.environment}-db"
  database_version = "POSTGRES_${var.postgres_version}"
  region           = var.region

  settings {
    tier = local.selected_tier.tier

    disk_size       = local.selected_tier.disk_size
    disk_type       = "PD_SSD"
    disk_autoresize = true

    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = var.environment == "prod"
      start_time                     = "03:00"
      transaction_log_retention_days = 7

      backup_retention_settings {
        retained_backups = var.backup_retention_days
      }
    }

    ip_configuration {
      ipv4_enabled    = false
      private_network = var.vpc_id
    }

    maintenance_window {
      day          = 7 # Sunday
      hour         = 3
      update_track = "stable"
    }

    insights_config {
      query_insights_enabled  = var.environment == "prod"
      query_string_length     = 1024
      record_application_tags = true
      record_client_address   = false
    }
  }

  deletion_protection = var.environment == "prod"
}

# Database
resource "google_sql_database" "main" {
  name     = var.database_name
  instance = google_sql_database_instance.main.name
}

# Generate random password
resource "random_password" "db_password" {
  length  = 32
  special = false
}

# Database User
resource "google_sql_user" "main" {
  name     = var.database_user
  instance = google_sql_database_instance.main.name
  password = random_password.db_password.result
}

# Store password in Secret Manager
resource "google_secret_manager_secret" "db_password" {
  secret_id = "${var.project}-${var.environment}-db-password"

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "db_password" {
  secret      = google_secret_manager_secret.db_password.id
  secret_data = random_password.db_password.result
}

# Store full connection string in Secret Manager
resource "google_secret_manager_secret" "db_connection_string" {
  secret_id = "${var.project}-${var.environment}-db-connection-string"

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "db_connection_string" {
  secret      = google_secret_manager_secret.db_connection_string.id
  secret_data = local.database_url
}

# Cloud Run Job for migrations (only if migration image is provided)
resource "google_cloud_run_v2_job" "migrations" {
  count    = var.migration_image != "" ? 1 : 0
  name     = "${var.project}-${var.environment}-migrations"
  location = var.region

  template {
    template {
      containers {
        image = var.migration_image

        env {
          name  = "DATABASE_URL"
          value = local.database_url
        }

        resources {
          limits = {
            cpu    = "1"
            memory = "512Mi"
          }
        }
      }

      # Connect to Cloud SQL via VPC
      dynamic "vpc_access" {
        for_each = var.vpc_connector_id != null ? [1] : []
        content {
          connector = var.vpc_connector_id
          egress    = "PRIVATE_RANGES_ONLY"
        }
      }

      timeout     = "${var.migration_timeout}s"
      max_retries = 1
    }
  }

  lifecycle {
    # Don't recreate on every deploy - job is triggered separately
    ignore_changes = [template[0].template[0].containers[0].image]
  }
}

# Outputs
output "connection_string" {
  description = "Database connection string"
  value       = local.database_url
  sensitive   = true
}

output "host" {
  description = "Database host (private IP)"
  value       = google_sql_database_instance.main.private_ip_address
}

output "instance_connection_name" {
  description = "Cloud SQL instance connection name for Cloud SQL Proxy"
  value       = google_sql_database_instance.main.connection_name
}

output "migration_job_name" {
  description = "Cloud Run Job name for migrations"
  value       = var.migration_image != "" ? google_cloud_run_v2_job.migrations[0].name : null
}

output "secret_id" {
  description = "Secret Manager secret ID for database password"
  value       = google_secret_manager_secret.db_password.secret_id
}

output "database_name" {
  description = "Database name"
  value       = google_sql_database.main.name
}

output "database_user" {
  description = "Database user name"
  value       = google_sql_user.main.name
}
