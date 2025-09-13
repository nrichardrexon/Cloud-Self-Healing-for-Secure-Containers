# ===============================
# Professional DevContainer Setup
# Cloud Self-Healing for Secure Containers
# ===============================

# Base Python image
FROM python:3.12-slim

# Environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV WORKSPACE=/workspace

# -------------------------------
# 1️⃣ Install system dependencies
# -------------------------------
RUN apt-get update && apt-get install -y \
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

# -------------------------------
# 2️⃣ Install kubectl
# -------------------------------
RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" \
    && chmod +x kubectl \
    && mv kubectl /usr/local/bin/

# -------------------------------
# 3️⃣ Install Helm
# -------------------------------
RUN curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# -------------------------------
# 4️⃣ Upgrade pip
# -------------------------------
RUN python -m pip install --upgrade pip

# -------------------------------
# 5️⃣ Create project folders
# -------------------------------
RUN mkdir -p $WORKSPACE/app \
    $WORKSPACE/monitoring \
    $WORKSPACE/remediator \
    $WORKSPACE/scripts \
    $WORKSPACE/docs

# -------------------------------
# 6️⃣ Set working directory
# -------------------------------
WORKDIR $WORKSPACE

# -------------------------------
# 7️⃣ Copy requirements.txt if exists and install Python packages
# -------------------------------
COPY requirements.txt .
RUN pip install -r requirements.txt || echo "No requirements.txt yet"

# -------------------------------
# 8️⃣ Default user (Codespaces)
# -------------------------------
USER root

# -------------------------------
# ✅ Container ready
# -------------------------------
CMD [ "bash" ]
