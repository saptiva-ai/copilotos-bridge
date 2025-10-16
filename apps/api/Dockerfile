# =========================================
# MULTI-STAGE DOCKERFILE FOR FASTAPI API
# =========================================
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# =========================================
# DEPENDENCIES STAGE
# =========================================
FROM base as deps

# Install system dependencies
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# =========================================
# DEVELOPMENT STAGE (includes testing tools)
# =========================================
FROM base as development

# Copy installed packages from deps stage
COPY --from=deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

# Install development dependencies
COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt

# Install runtime dependencies (MVP-OCR: Added tesseract-ocr for image text extraction)
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    curl \
    tesseract-ocr \
    tesseract-ocr-spa \
    tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user
RUN useradd --create-home --shell /bin/bash --uid 1001 api_user

# Copy application code
COPY --chown=api_user:api_user . .

# Switch to non-root user
USER api_user

# Add local bin to PATH for pytest and other tools
ENV PATH="/home/api_user/.local/bin:${PATH}"

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8001/api/health || exit 1

# Run application with hot reload
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8001", "--reload"]

# =========================================
# PRODUCTION STAGE
# =========================================
FROM base as production

# Copy installed packages from deps stage
COPY --from=deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

# Install only runtime dependencies (MVP-OCR: Added tesseract-ocr for image text extraction)
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    curl \
    tesseract-ocr \
    tesseract-ocr-spa \
    tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user
RUN useradd --create-home --shell /bin/bash --uid 1001 api_user

# Copy application code
COPY --chown=api_user:api_user . .

# Switch to non-root user
USER api_user

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8001/api/health || exit 1

# Run application
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "1"]