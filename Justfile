# Stack Bench — cross-language orchestration

# Start all services
dev:
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
    cd app/backend && just migrate

seed:
    cd app/backend && just seed

# CLI
test-cli:
    cd app/cli && just test

quality-cli:
    cd app/cli && just quality

build-cli:
    cd app/cli && just build
