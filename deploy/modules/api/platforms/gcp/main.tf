# GCP Cloud Run API Module
# Deploys a containerized API to Cloud Run

resource "google_cloud_run_v2_service" "api" {
  name     = var.name
  location = var.region

  template {
    containers {
      image = var.image

      ports {
        container_port = var.port
      }

      # Resource limits based on size tier
      resources {
        limits = {
          cpu    = var.cpu
          memory = var.memory
        }
        cpu_idle = true  # Allow CPU to idle (for scale-to-zero cost savings)
      }

      # Core environment variables
      dynamic "env" {
        for_each = var.database_url != "" ? [1] : []
        content {
          name  = "DATABASE_URL"
          value = var.database_url
        }
      }

      dynamic "env" {
        for_each = var.redis_url != "" ? [1] : []
        content {
          name  = "REDIS_URL"
          value = var.redis_url
        }
      }

      # Environment indicator
      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }

      # Additional environment variables
      dynamic "env" {
        for_each = var.extra_env
        content {
          name  = env.key
          value = env.value
        }
      }

      # Secrets from Secret Manager
      dynamic "env" {
        for_each = var.extra_secrets
        content {
          name = env.key
          value_source {
            secret_key_ref {
              secret  = env.value
              version = "latest"
            }
          }
        }
      }

      # Startup probe - longer timeout for cold starts
      startup_probe {
        http_get {
          path = var.health_path
          port = var.port
        }
        initial_delay_seconds = var.startup_initial_delay
        timeout_seconds       = var.startup_timeout
        period_seconds        = 10
        failure_threshold     = 10
      }

      # Liveness probe - ongoing health checks
      liveness_probe {
        http_get {
          path = var.health_path
          port = var.port
        }
        period_seconds    = var.liveness_interval
        timeout_seconds   = var.liveness_timeout
        failure_threshold = 3
      }
    }

    # Scaling configuration
    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }

    # VPC Access Connector for private network connectivity (Cloud SQL, etc.)
    dynamic "vpc_access" {
      for_each = var.vpc_connector_id != null ? [1] : []
      content {
        connector = var.vpc_connector_id
        egress    = "PRIVATE_RANGES_ONLY"
      }
    }

    # Service account (optional, uses default if not specified)
    # service_account = var.service_account

    # Timeout for requests
    timeout = "300s"

    # Labels for organization
    labels = {
      environment = var.environment
      managed-by  = "pattern-stack"
    }
  }

  # Traffic configuration - all traffic to latest revision
  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  # Labels for the service
  labels = {
    environment = var.environment
    managed-by  = "pattern-stack"
  }

  lifecycle {
    # Prevent accidental deletion
    prevent_destroy = false
  }
}

# IAM binding for public access (if enabled)
resource "google_cloud_run_v2_service_iam_member" "public" {
  count    = var.public ? 1 : 0
  location = google_cloud_run_v2_service.api.location
  name     = google_cloud_run_v2_service.api.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Outputs
output "url" {
  description = "Public URL of the Cloud Run service"
  value       = google_cloud_run_v2_service.api.uri
}

output "revision" {
  description = "Latest ready revision name"
  value       = google_cloud_run_v2_service.api.latest_ready_revision
}

output "service_id" {
  description = "Cloud Run service ID"
  value       = google_cloud_run_v2_service.api.id
}
