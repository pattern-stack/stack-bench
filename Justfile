# Stack Bench — cross-language orchestration

# Start all services (secrets injected from 1Password)
dev:
    op run --env-file=.env.example -- pts dev

# Start without 1Password (requires app/backend/.env to have secrets)
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

# Deploy
deploy-build *args='':
    #!/usr/bin/env bash
    set -euo pipefail
    export GITHUB_TOKEN=$(gh auth token)
    tag=${1:-$(git rev-parse --short HEAD)}
    registry=$(grep -A5 'registry:' patterns.yaml | grep 'region:' | awk '{print $2}')-docker.pkg.dev/$(grep -A5 'gcp:' patterns.yaml | grep 'project_id:' | awk '{print $2}')/$(grep 'project:' patterns.yaml | head -1 | awk '{print $2}')
    echo "Building backend → $registry/backend:$tag"
    docker build --platform linux/amd64 --secret id=GITHUB_TOKEN,env=GITHUB_TOKEN -f app/backend/Dockerfile -t "$registry/backend:$tag" .
    echo "Building frontend → $registry/frontend:$tag"
    docker build --platform linux/amd64 -f app/frontend/Dockerfile -t "$registry/frontend:$tag" .
    docker tag "$registry/backend:$tag" "$registry/backend:latest"
    docker tag "$registry/frontend:$tag" "$registry/frontend:latest"
    echo "Done. Push with: just deploy-push $tag"

deploy-push tag='':
    #!/usr/bin/env bash
    set -euo pipefail
    tag=${1:-$(git rev-parse --short HEAD)}
    registry=$(grep -A5 'registry:' patterns.yaml | grep 'region:' | awk '{print $2}')-docker.pkg.dev/$(grep -A5 'gcp:' patterns.yaml | grep 'project_id:' | awk '{print $2}')/$(grep 'project:' patterns.yaml | head -1 | awk '{print $2}')
    echo "Pushing $registry/backend:$tag"
    docker push "$registry/backend:$tag"
    echo "Pushing $registry/frontend:$tag"
    docker push "$registry/frontend:$tag"
    echo "Pushing :latest tags"
    docker push "$registry/backend:latest"
    docker push "$registry/frontend:latest"

deploy-release *args='': (deploy-build args)
    #!/usr/bin/env bash
    set -euo pipefail
    tag=${1:-$(git rev-parse --short HEAD)}
    just deploy-push "$tag"
    pts deploy apply
