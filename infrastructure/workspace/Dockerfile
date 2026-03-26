# infrastructure/workspace/Dockerfile
#
# Workspace server container -- runs inside Cloud Run, provides
# file/git/terminal access for agents working on a repository.

FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    python3 \
    python3-pip \
    python3-venv \
    openssh-client \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -s /bin/bash workspace

# App directory
WORKDIR /app

# Python deps
COPY server/requirements.txt /app/requirements.txt
RUN python3 -m venv /app/.venv && \
    /app/.venv/bin/pip install --no-cache-dir -r /app/requirements.txt

# Copy server code
COPY server/ /app/server/

# Workspace directory (repo clone target)
RUN mkdir -p /workspace && chown workspace:workspace /workspace

# Switch to non-root
USER workspace

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"

EXPOSE 8080

ENTRYPOINT ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8080"]
