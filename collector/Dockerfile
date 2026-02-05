# Build stage
FROM python:3.13-alpine AS builder

WORKDIR /app

# Install build dependencies
RUN apk add --no-cache \
    gcc \
    musl-dev \
    postgresql-dev \
    python3-dev

# Install uv
RUN pip install --no-cache-dir uv

# Copy pyproject.toml to install dependencies
COPY pyproject.toml .

# Install Python dependencies to a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN uv pip install --no-cache-dir .

# Production stage
FROM python:3.13-alpine AS production

WORKDIR /app

# Install only runtime dependencies
RUN apk add --no-cache \
    postgresql-libs \
    curl \
    && rm -rf /var/cache/apk/*

# Copy the virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy source code
COPY . /app/src/

# Create non-root user
RUN addgroup -g 1001 -S apiuser && adduser -u 1001 -S apiuser -G apiuser

# Change ownership of app directory
RUN chown -R apiuser:apiuser /app

USER apiuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

CMD ["python", "-m", "src.api.main"]
