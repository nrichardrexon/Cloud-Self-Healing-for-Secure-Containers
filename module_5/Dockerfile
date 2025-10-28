# =========================================
# ✅ Final Dockerfile (Module 5 – Fault Injector, Stable Prometheus Version)
# =========================================

# Base lightweight Python image
FROM python:3.12-slim

# Set working directory inside container
WORKDIR /app

# -------------------------------------------------
# 1️⃣ Install dependencies (build-time only)
# -------------------------------------------------
COPY module_5/requirements.txt ./requirements.txt

USER root

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl gcc build-essential ca-certificates gnupg \
    && pip install --no-cache-dir -r requirements.txt prometheus_client flask \
    \
    # -------------------------------------------------
    # 🧩 Install kubectl (latest stable release)
    # -------------------------------------------------
    && KUBECTL_VERSION="$(curl -L -s https://dl.k8s.io/release/stable.txt)" \
    && curl -LO "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl" \
    && install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl \
    && rm kubectl \
    \
    # -------------------------------------------------
    # 🧹 Cleanup
    # -------------------------------------------------
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# -------------------------------------------------
# 2️⃣ Copy module files (explicit paths since build context is repo root)
# -------------------------------------------------
COPY module_5/app ./app
COPY module_5/scripts ./scripts
COPY module_5/policies.yaml ./policies.yaml

# -------------------------------------------------
# 3️⃣ Expose metrics port (Prometheus)
# -------------------------------------------------
EXPOSE 9090

# -------------------------------------------------
# 4️⃣ Create non-root user for runtime security
# -------------------------------------------------
RUN useradd -m faultinjectoruser
USER faultinjectoruser

# -------------------------------------------------
# 5️⃣ Add lightweight metrics server
# Keeps container alive + provides /metrics endpoint
# -------------------------------------------------
COPY <<'EOF' ./metrics_server.py
from flask import Flask, Response
from prometheus_client import CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST, Gauge

app = Flask(__name__)
registry = CollectorRegistry()
status_gauge = Gauge('faultinjector_status', 'Current status of fault injector', registry=registry)

@app.route('/metrics')
def metrics():
    status_gauge.set(1)
    return Response(generate_latest(registry), mimetype=CONTENT_TYPE_LATEST)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=9090)
EOF

# -------------------------------------------------
# 6️⃣ Default entrypoint — start both metrics and injector
# -------------------------------------------------
CMD ["sh", "-c", "python metrics_server.py & python scripts/fault_injection.py"]
