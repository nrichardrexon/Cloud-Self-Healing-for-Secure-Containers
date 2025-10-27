# =========================================
# ✅ Corrected Dockerfile (Module 5 – Fault Injector)
# =========================================

# Base lightweight Python image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# -------------------------------------------------
# 1️⃣ Install dependencies
# -------------------------------------------------
COPY requirements.txt ./requirements.txt
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl gcc build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir -r requirements.txt

# -------------------------------------------------
# 2️⃣ Copy fault injection code & policies
# -------------------------------------------------
COPY app/ ./app
COPY policies.yaml ./policies.yaml

# -------------------------------------------------
# 3️⃣ Create non-root user (security best practice)
# -------------------------------------------------
RUN useradd -m faultinjectoruser
USER faultinjectoruser

# -------------------------------------------------
# 4️⃣ Default behavior — run the fault injector loop
# -------------------------------------------------
CMD ["python", "app/main.py"]
