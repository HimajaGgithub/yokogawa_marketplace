FROM python:3.13-slim AS base

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl ca-certificates git && \
    \
    # Use curl to install uv
    curl -LsSf https://astral.sh/uv/install.sh | sh && \
    \
    # Clean up the build tools
    apt-get remove -y curl git && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

# Ensure uv is in PATH
ENV PATH="/root/.local/bin:${PATH}"

WORKDIR /app
COPY dist/base_image/pyproject.toml dist/base_image/uv.lock ./

# Install dependencies
RUN uv sync --frozen
