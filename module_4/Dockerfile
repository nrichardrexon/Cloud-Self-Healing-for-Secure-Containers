# ==========================================
# 🧠 Remediator Dockerfile (Kind-Compatible, Final Stable)
# ==========================================

FROM python:3.12-slim

WORKDIR /app

# ---------------------------------------------------------
# Environment configuration
# ---------------------------------------------------------
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/home/appuser/.local/bin:$PATH"
ENV LOG_DIR="/tmp/logs"
ENV ENABLE_METRICS="true"
ENV COOLDOWN_SECONDS="60"
ENV POLICIES_FILE="/app/policies.yaml"

# ---------------------------------------------------------
# System packages (for subprocess + network tools)
# ---------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl gcc build-essential ca-certificates net-tools iputils-ping \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------
# ✅ Copy requirements first for layer caching
# ---------------------------------------------------------
COPY requirements.txt ./requirements.txt

# ---------------------------------------------------------
# Install dependencies
# ---------------------------------------------------------
RUN pip install --no-cache-dir -r requirements.txt

# ---------------------------------------------------------
# ✅ Copy application code and policies
# ---------------------------------------------------------
COPY app/ ./app
COPY policies.yaml ./policies.yaml

# ---------------------------------------------------------
# Create writable log directory (for non-root user)
# ---------------------------------------------------------
RUN mkdir -p /tmp/logs && chmod -R 777 /tmp/logs

# ---------------------------------------------------------
# Create non-root user and switch to it
# ---------------------------------------------------------
RUN useradd -m appuser
USER appuser

# ---------------------------------------------------------
# Network + Health
# ---------------------------------------------------------
EXPOSE 8080

# Built-in FastAPI /health probe for K8s
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
  CMD curl -fs http://localhost:8080/health || exit 1

# ---------------------------------------------------------
# ✅ Launch Remediator (FastAPI via Uvicorn)
# ---------------------------------------------------------
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
