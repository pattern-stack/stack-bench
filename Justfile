# Stack Bench — cross-language orchestration

# List available recipes
default:
    @just --list

# ── All ──────────────────────────────────────────

# Start all services
dev:
    pts dev

# Run all tests
test: test-backend test-cli

# Run all quality gates
quality: quality-backend quality-cli

# ── Backend ──────────────────────────────────────

# Run backend tests
test-backend:
    cd app/backend && just test

# Run backend quality gates
quality-backend:
    cd app/backend && just quality

# Run database migrations
migrate:
    cd app/backend && just migrate

# Seed database
seed:
    cd app/backend && just seed

# ── CLI ──────────────────────────────────────────

# Build CLI binary
build-cli:
    cd app/cli && just build

# Run CLI
run-cli *args:
    cd app/cli && just run {{args}}

# Run CLI tests
test-cli:
    cd app/cli && just test

# Run CLI quality gates
quality-cli:
    cd app/cli && just quality

# Run CLI in demo mode (hands-free replay)
demo-cli *args:
    cd app/cli && just demo {{args}}

# Show CLI component gallery
gallery:
    cd app/cli && just gallery

# Run CLI in tmux for AI-driven testing
demo-tmux *args:
    cd app/cli && just demo-tmux {{args}}
