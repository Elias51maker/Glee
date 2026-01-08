FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_SYSTEM_PYTHON=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --no-cache-dir uv

# Install AI CLI tools globally
RUN npm install -g \
    @openai/codex \
    @anthropic-ai/claude-code \
    @google/gemini-cli \
    @charmland/crush \
    opencode

WORKDIR /app

# Copy project files
COPY pyproject.toml uv.lock ./
COPY glee/ ./glee/
COPY README.md ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Create data directory
RUN mkdir -p /app/.glee/sessions

# Expose port for SSE transport (future)
EXPOSE 8080

# Default command - run as MCP server via stdio
CMD ["uv", "run", "python", "-m", "glee"]
