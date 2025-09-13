# ===============================
# Professional DevContainer Setup
# Cloud Self-Healing for Secure Containers
# ===============================

# Base image: Python 3.12 + Node LTS preinstalled
FROM mcr.microsoft.com/devcontainers/python:3.12-node

# ===============================
# Environment Variables
# ===============================
ENV DEBIAN_FRONTEND=noninteractive
ENV WORKSPACE=/workspace

# ===============================
# 1️⃣ Install system dependencies
# ===============================
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    gnupg \
    lsb-release \
    ca-certificates \
    openssl \
    git \
    bash-completion \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# ===============================
# 2️⃣ Install kubectl
# ===============================
RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" \
    && install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl \
    && rm kubectl

# ===============================
# 3️⃣ Install Helm
# ===============================
RUN curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# ===============================
# 4️⃣ Upgrade pip (Python package manager)
# ===============================
RUN python -m pip install --upgrade pip setuptools wheel

# ===============================
# 5️⃣ Create project folders
# ===============================
RUN mkdir -p $WORKSPACE/app \
    $WORKSPACE/monitoring \
    $WORKSPACE/remediator \
    $WORKSPACE/scripts \
    $WORKSPACE/docs

# ===============================
# 6️⃣ Set working directory
# ===============================
WORKDIR $WORKSPACE

# ===============================
# 7️⃣ Copy requirements.txt and install Python packages safely
# ===============================
COPY requirements.txt . 
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; else echo "No requirements.txt found, skipping"; fi

# ===============================
# 8️⃣ Default user
# ===============================
USER root

# ===============================
# ✅ Container ready
# ===============================
CMD ["bash"]
