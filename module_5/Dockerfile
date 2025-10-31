# =========================================
# ✅ Final Dockerfile (Module 5 – Fault Injector, Stable & Safe Build)
# =========================================

# 🐍 Base lightweight Python image
FROM python:3.12-slim

# Set working directory inside container
WORKDIR /app

# -------------------------------------------------
# 1️⃣ Install dependencies (system + Python)
# -------------------------------------------------
USER root

# Copy dependency file early for Docker layer caching
COPY module_5/requirements.txt ./requirements.txt

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl gcc build-essential ca-certificates gnupg procps iputils-ping stress-ng \
    && pip install --no-cache-dir -r requirements.txt prometheus_client flask \
    \
    # 🧩 Install latest kubectl safely
    && KUBECTL_VERSION="$(curl -L -s https://dl.k8s.io/release/stable.txt)" \
    && curl -LO "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl" \
    && install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl \
    && rm kubectl \
    \
    # 🧹 Cleanup to minimize image size
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# -------------------------------------------------
# 2️⃣ Copy application files
# -------------------------------------------------
COPY module_5/app ./app
COPY module_5/scripts ./scripts
COPY module_5/policies.yaml ./policies.yaml

# -------------------------------------------------
# 3️⃣ Expose metrics port for Prometheus scraping
# -------------------------------------------------
EXPOSE 9090

# -------------------------------------------------
# 4️⃣ Inline lightweight metrics server
# -------------------------------------------------
RUN printf '%s\n' \
"from flask import Flask, Response" \
"from prometheus_client import CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST, Gauge" \
"" \
"app = Flask(__name__)" \
"registry = CollectorRegistry()" \
"status_gauge = Gauge('faultinjector_status', 'Current status of fault injector', registry=registry)" \
"" \
"@app.route('/metrics')" \
"def metrics():" \
"    status_gauge.set(1)" \
"    return Response(generate_latest(registry), mimetype=CONTENT_TYPE_LATEST)" \
"" \
"if __name__ == '__main__':" \
"    app.run(host='0.0.0.0', port=9090)" \
> /app/metrics_server.py

# -------------------------------------------------
# 5️⃣ Secure runtime: non-root user setup
# -------------------------------------------------
RUN useradd -m faultinjectoruser && chown -R faultinjectoruser /app
USER faultinjectoruser

# -------------------------------------------------
# 6️⃣ Default command (metrics + fault injector)
# -------------------------------------------------
CMD ["sh", "-c", "python /app/metrics_server.py & python /app/scripts/fault_injection.py"]
