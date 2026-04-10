FROM python:3.12-slim

WORKDIR /app

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    rm -rf /var/lib/apt/lists/*

# Copy dependency spec first (layer caching: only re-installs when deps change)
COPY pyproject.toml .

# Copy application source (needed before editable install)
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -e ".[dev]"

# Create default data directories
RUN mkdir -p /data/hermes_memory_engine/structural \
             /data/hermes_memory_engine/semantic/chroma_db

ENV PYTHONUNBUFFERED=1
ENV HERMES_HOME=/opt/data

# Default: run MCP server. Override CMD for other entrypoints:
#   docker run <image> test       — run the test suite
#   docker run <image> mcp        — run the MCP server (default)
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
CMD ["mcp"]
