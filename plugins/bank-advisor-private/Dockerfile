# BankAdvisor MCP Server Dockerfile - Optimized with uv + hot reload
FROM python:3.11-slim-bookworm

# Set working directory
WORKDIR /app

# Install system dependencies + uv
RUN apt-get update && apt-get install -y \
    postgresql-client \
    libpq-dev \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && curl -LsSf https://astral.sh/uv/install.sh | sh

# Add uv to PATH
ENV PATH="/root/.local/bin:$PATH"

# Copy requirements first (for better caching)
COPY plugins/bank-advisor-private/requirements.txt .

# Install Python dependencies with uv (much faster than pip)
RUN uv pip install --system --no-cache -r requirements.txt

# Copy application code from plugin directory
COPY plugins/bank-advisor-private/src/ ./src/
COPY plugins/bank-advisor-private/data/ ./data/
COPY plugins/bank-advisor-private/migrations/ ./migrations/
COPY plugins/bank-advisor-private/config/ ./config/
COPY plugins/bank-advisor-private/etl/ ./etl/

# Copy and setup entrypoint script for automatic ETL initialization
# Use sed to fix Windows line endings (CRLF -> LF)
COPY plugins/bank-advisor-private/scripts/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN sed -i 's/\r$//' /usr/local/bin/docker-entrypoint.sh && chmod +x /usr/local/bin/docker-entrypoint.sh

# Set PYTHONPATH to include src directory
ENV PYTHONPATH=/app/src

# Environment variable for hot reload (dev mode)
ENV UVICORN_RELOAD=true

# Expose MCP Server port
EXPOSE 8002

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

# Set entrypoint to run ETL initialization before starting server
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

# Start the MCP server via uvicorn with hot reload
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8002", "--reload", "--reload-dir", "/app/src"]
