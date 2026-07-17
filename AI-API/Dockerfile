# ═══════════════════════════════════════════════════════════════
# Stage 1 — Install dependencies
# ═══════════════════════════════════════════════════════════════
FROM python:3.11-slim AS builder

WORKDIR /app

# System dependencies cho build
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc g++ libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install TẤT CẢ packages dùng --extra-index-url CPU-only
# Khi timm/smp kéo torch, pip sẽ ưu tiên lấy từ CPU index
RUN pip install --no-cache-dir --prefix=/install \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    -r requirements.txt

# ═══════════════════════════════════════════════════════════════
# Stage 2 — Final image
# ═══════════════════════════════════════════════════════════════
FROM python:3.11-slim

WORKDIR /app

# Runtime dependencies cho OpenCV (headless chỉ cần libglib)
RUN apt-get update && \
    apt-get install -y --no-install-recommends libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*

# Copy installed packages từ builder
COPY --from=builder /install /usr/local

# Copy model weights (lớn nhất, cache Docker layer)
COPY ai_models/ ./ai_models/

# Copy application code
COPY app/ ./app/
COPY data/ ./data/
COPY .env* ./

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=120s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/health')" || exit 1

# Start server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
