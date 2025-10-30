# =========================================
# ✅ Module 5 – Fault Injector Deployment Script (Final Fixed Version)
# =========================================

import subprocess
import os
import sys
import time
import yaml
from pathlib import Path

# -------------------------------------------------
# Constants & Paths
# -------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
MODULE5_DIR = BASE_DIR / "module_5"
DEPLOYMENT_YAML = MODULE5_DIR / "k8s" / "test-deployment.yaml"
LOCAL_IMAGE = "module5-faultinjector:latest"
KIND_CLUSTER_NAME = "selfhealing-cluster"
NAMESPACE = "monitoring"
LABEL_SELECTOR = "app=faultinjector"

# -------------------------------------------------
# Utility function
# -------------------------------------------------
def run_command(cmd, check=True):
    print(f"\nRunning: {cmd}")
    try:
        result = subprocess.run(
            cmd, shell=True, text=True, capture_output=True, check=check
        )
        if result.stdout:
            print(result.stdout.strip())
        if result.stderr and not check:
            print(result.stderr.strip())
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Command failed:\n{e.output}")
        if check:
            sys.exit(1)
        return ""

# -------------------------------------------------
# Kind cluster helpers
# -------------------------------------------------
def is_kind_installed():
    return run_command("kind --version", check=False) != ""

def install_kind():
    print("Installing Kind in ~/bin...")
    run_command("mkdir -p ~/bin")
    run_command("curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.25.0/kind-linux-amd64")
    run_command("chmod +x ./kind && mv ./kind ~/bin/")
    bashrc_path = os.path.expanduser("~/.bashrc")
    with open(bashrc_path, "a") as f:
        f.write("\nexport PATH=$HOME/bin:$PATH\n")
    os.environ["PATH"] = f"{os.path.expanduser('~/bin')}:" + os.environ["PATH"]
    print("✅ Kind installed. PATH updated.")

def create_kind_cluster():
    clusters = run_command("kind get clusters", check=False).splitlines()
    if KIND_CLUSTER_NAME in clusters:
        print("✅ Kind cluster already exists.")
        return
    print(f"Creating Kind cluster '{KIND_CLUSTER_NAME}'...")
    run_command(f"kind create cluster --name {KIND_CLUSTER_NAME} --wait 60s")
    print("✅ Kind cluster ready.")

def load_image_into_kind():
    print(f"📦 Loading {LOCAL_IMAGE} into Kind cluster...")
    run_command(f"kind load docker-image {LOCAL_IMAGE} --name {KIND_CLUSTER_NAME}")
    print("✅ Image loaded into Kind cluster.")

# -------------------------------------------------
# Cleanup old pods and ReplicaSets
# -------------------------------------------------
def cleanup_old_resources():
    print("🗑 Cleaning up old pods and ReplicaSets...")
    pods = run_command(f"kubectl get pods -l {LABEL_SELECTOR} -n {NAMESPACE} -o name", check=False)
    if pods:
        for pod in pods.splitlines():
            run_command(f"kubectl delete {pod} -n {NAMESPACE}", check=False)

    replicasets = run_command(f"kubectl get rs -l {LABEL_SELECTOR} -n {NAMESPACE} -o name", check=False)
    if replicasets:
        for rs in replicasets.splitlines():
            run_command(f"kubectl delete {rs} -n {NAMESPACE}", check=False)
    print("✅ Old resources cleaned up.")

# -------------------------------------------------
# Build Docker image from repo root
# -------------------------------------------------
def build_local_image():
    print(f"🛠 Building local image {LOCAL_IMAGE} with correct build context...")
    repo_root = BASE_DIR
    dockerfile_path = MODULE5_DIR / "Dockerfile"
    cmd = f"docker build -t {LOCAL_IMAGE} -f {dockerfile_path} {repo_root}"
    run_command(cmd)

# -------------------------------------------------
# Patch Deployment YAML
# -------------------------------------------------
def patch_deployment_for_local_image():
    print("➡ Patching Deployment YAML for local image usage...")
    with open(DEPLOYMENT_YAML, "r") as f:
        deployment_docs = list(yaml.safe_load_all(f))

    for doc in deployment_docs:
        if doc.get("kind") == "Deployment":
            for container in doc["spec"]["template"]["spec"]["containers"]:
                container["image"] = LOCAL_IMAGE
                container["imagePullPolicy"] = "IfNotPresent"

    with open(DEPLOYMENT_YAML, "w") as f:
        yaml.safe_dump_all(deployment_docs, f)

    print("✅ Deployment YAML patched.")

# -------------------------------------------------
# Apply K8s Deployment
# -------------------------------------------------
def apply_k8s_resources():
    print("🚀 Applying Kubernetes resources...")
    run_command(f"kubectl apply -f {DEPLOYMENT_YAML}")

# -------------------------------------------------
# Wait for pod readiness
# -------------------------------------------------
def wait_for_pods():
    print("⏳ Waiting for pods to be ready...")
    for _ in range(12):  # 1 min timeout
        time.sleep(5)
        status = run_command(
            f"kubectl get pods -l {LABEL_SELECTOR} -n {NAMESPACE} "
            "-o jsonpath='{.items[*].status.containerStatuses[*].ready}'",
            check=False
        )
        if "true" in status.lower():
            print("✅ All pods are ready!")
            return
        else:
            print("⏳ Pods not ready yet. Retrying...")
    print("❌ Pods failed to become ready in time. Check logs manually.")

# -------------------------------------------------
# Main Routine
# -------------------------------------------------
def deploy_module_5():
    print("\n============================================")
    print("🚀 Starting Module 5 – Fault Injector Deployment")
    print("============================================")

    if not is_kind_installed():
        install_kind()

    create_kind_cluster()
    cleanup_old_resources()
    build_local_image()
    load_image_into_kind()
    patch_deployment_for_local_image()
    apply_k8s_resources()
    wait_for_pods()

    print("\n✅ Module 5 deployment complete.")

# -------------------------------------------------
if __name__ == "__main__":
    deploy_module_5()
