# =========================================
# ✅ Final Dockerfile (Module 5 – Fault Injector)
# =========================================

# Base lightweight Python image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# -------------------------------------------------
# 1️⃣ Install dependencies (build-time only)
# -------------------------------------------------
COPY module_5/requirements.txt ./requirements.txt

# Use root for setup
USER root

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl gcc build-essential \
    && pip install --no-cache-dir -r requirements.txt \
    && rm -rf /var/lib/apt/lists/*

# -------------------------------------------------
# 2️⃣ Copy fault injection code & policies
# -------------------------------------------------
COPY module_5/app ./app
COPY module_5/scripts ./scripts
COPY module_5/policies.yaml ./policies.yaml

# -------------------------------------------------
# 3️⃣ Expose metrics port (needed by Prometheus)
# -------------------------------------------------
EXPOSE 9090

# -------------------------------------------------
# 4️⃣ Create non-root user (for runtime security)
# -------------------------------------------------
RUN useradd -m faultinjectoruser
USER faultinjectoruser

# -------------------------------------------------
# 5️⃣ Default entrypoint — run the fault injector
# -------------------------------------------------
CMD ["python", "scripts/fault_injection.py"]
