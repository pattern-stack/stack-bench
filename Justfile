# Stack Bench — cross-language orchestration

# Start all services (secrets injected from 1Password)
# Set OP_ACCOUNT env var to select 1Password account
dev:
    op run --env-file=.env.example -- pts dev

# Start without 1Password (requires app/.env to exist)
dev-local:
    pts dev

# Run all tests
test: test-backend test-cli

# Run all quality gates
quality: quality-backend quality-cli

# Backend
test-backend:
    cd app/backend && just test

quality-backend:
    cd app/backend && just quality

migrate:
    op run --env-file=.env.example -- just _migrate

_migrate:
    cd app/backend && just migrate

seed:
    op run --env-file=.env.example -- just _seed

_seed:
    cd app/backend && just seed

# CLI
test-cli:
    cd app/cli && just test

quality-cli:
    cd app/cli && just quality

build-cli:
    cd app/cli && just build
