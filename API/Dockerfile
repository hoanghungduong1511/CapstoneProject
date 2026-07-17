# ═══════════════════════════════════════════════════════════════
# Stage 1 — Build dependencies
# ═══════════════════════════════════════════════════════════════
FROM python:3.11-slim AS builder

WORKDIR /app

# Cài đặt system dependencies cho psycopg2
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ═══════════════════════════════════════════════════════════════
# Stage 2 — Final image
# ═══════════════════════════════════════════════════════════════
FROM python:3.11-slim

WORKDIR /app

# Runtime dependency cho PostgreSQL
RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq5 && \
    rm -rf /var/lib/apt/lists/*

# Copy installed packages từ builder
COPY --from=builder /install /usr/local

# Copy entrypoint script
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Copy source code
COPY . .

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/')" || exit 1

# Entrypoint: chạy migration + start server
ENTRYPOINT ["/docker-entrypoint.sh"]
