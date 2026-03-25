# GCP Prod Environment
# Project: stack-bench

environment = "prod"
registry_url = "northamerica-northeast2-docker.pkg.dev/stack-bench/stack-bench"

project_id = "stack-bench"
region     = "northamerica-northeast2"
vpc_name   = "default"

# Required for deployment
domain    = "prod.stack-bench.example.com"  # TODO: Update with actual domain
image_tag = "latest"

# Scaling: auto = scale-to-zero (2-5s cold starts, saves ~$20-40/mo per service)
# Use "always-on" if cold starts are unacceptable
scaling_mode = "auto"
