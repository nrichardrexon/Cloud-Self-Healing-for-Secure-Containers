# ===============================
# Professional DevContainer Setup
# Cloud Self-Healing for Secure Containers
# ===============================

# Use a full Debian-based Python image for reliability
FROM python:3.12-bullseye

# -------------------------------
# Environment variables
# -------------------------------
ENV DEBIAN_FRONTEND=noninteractive   # Avoid interactive prompts during apt installs
ENV WORKSPACE=/workspace             # Define workspace folder

# -------------------------------
# 1️⃣ Install system dependencies
# -------------------------------
# curl, wget: download files
# gnupg, lsb-release, ca-certificates: secure package verification
# openssl: required for Helm and other tools
# git: version control
# bash-completion: optional usability enhancement
# unzip: for extracting archives if needed
RUN apt-get update && apt-get install -y \
    curl wget gnupg lsb-release ca-certificates \
    openssl git bash-completion unzip \
    && rm -rf /var/lib/apt/lists/*

# -------------------------------
# 2️⃣ Install kubectl (Kubernetes CLI)
# -------------------------------
# Download the latest stable release of kubectl
# Make it executable and move it to /usr/local/bin
RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" \
    && chmod +x kubectl \
    && mv kubectl /usr/local/bin/

# -------------------------------
# 3️⃣ Install Helm (Kubernetes package manager)
# -------------------------------
# Use Helm install script from official repo
# Helm is required for installing Prometheus and other charts
RUN curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# -------------------------------
# 4️⃣ Upgrade pip (Python package manager)
# -------------------------------
RUN python -m pip install --upgrade pip

# -------------------------------
# 5️⃣ Create project folders
# -------------------------------
# Standard folders for app, monitoring, remediator, scripts, docs
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
# Using wildcard in case file is missing to avoid build failure
COPY requirements.txt* .
RUN pip install -r requirements.txt || echo "No requirements.txt yet"

# -------------------------------
# 8️⃣ Default user
# -------------------------------
# Codespaces defaults to root for simplicity
USER root

# -------------------------------
# 9️⃣ Default command
# -------------------------------
CMD ["bash"]

# ✅ Container ready with:
# - Python 3.12
# - kubectl
# - Helm
# - Project folders created
# - pip updated and requirements installed
