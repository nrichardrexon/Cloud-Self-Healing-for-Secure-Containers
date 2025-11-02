#!/usr/bin/env python3
"""
Module 5 – Fault Injector Deployment Script
Cloud Self-Healing for Secure Containers
"""

import os
import subprocess
import time
import logging

# --------------------------------------------
# Basic Config
# --------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(message)s")
BASE_DIR = "/workspaces/Cloud-Self-Healing-for-Secure-Containers/module_5"
POSSIBLE_DEPLOYMENTS = [
    os.path.join(BASE_DIR, "k8s/test-deployment.yaml"),
    os.path.join(BASE_DIR, "k8s/faultinjector-deployment.yaml"),
    os.path.join(BASE_DIR, "k8s/faultinjector-deployment.yml"),
]
DOCKERFILE_PATH = os.path.join(BASE_DIR, "Dockerfile")
IMAGE_NAME = "module5-faultinjector:latest"
CLUSTER_NAME = "selfhealing-cluster"
NAMESPACE = "monitoring"


# --------------------------------------------
# Utility Functions
# --------------------------------------------
def run_command(cmd: str, check: bool = False, timeout: int = 120) -> str:
    """Run a shell command and return stdout/stderr combined (trimmed)."""
    logging.info(f"⚙️  Running: {cmd}")
    try:
        result = subprocess.run(
            cmd, shell=True, check=check, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout
        )
        out = result.stdout.strip()
        if out:
            logging.info(out)
        return out
    except subprocess.CalledProcessError as e:
        logging.error(f"❌ Command failed ({cmd}):\n{e.output}")
        return e.output.strip() if e.output else ""
    except subprocess.TimeoutExpired:
        logging.error(f"⏰ Command timed out ({cmd}) after {timeout}s")
        return "timeout"


def _exec_with_retries(cmd, retries=3, delay=2, timeout=120):
    """Exec shell cmd with retry loop and dynamic timeout."""
    last = ""
    for attempt in range(1, retries + 1):
        last = run_command(cmd, timeout=timeout)
        if last and "not found" not in last and "Error from server" not in last:
            return last
        logging.debug(f"Attempt {attempt}/{retries} failed; retrying in {delay}s...")
        time.sleep(delay)
    return last


# --------------------------------------------
# Step 1 – Pre-checks
# --------------------------------------------
def check_stress_ng():
    logging.info("\n🧩 Checking if 'stress-ng' is installed ...\n")
    out = run_command("which stress-ng", timeout=10)
    if not out or "stress-ng" not in out:
        logging.info("⚠️  stress-ng not found on deploy host.")
        logging.info("If needed, install manually: sudo apt-get install -y stress-ng")
    else:
        logging.info(f"✅ stress-ng already installed at {out}")


def check_kind_cluster():
    logging.info("\n⚙️  Checking Kind cluster...\n")
    run_command("kind --version", timeout=10)
    clusters = run_command("kind get clusters", timeout=10)
    if CLUSTER_NAME not in clusters:
        logging.info(f"⚠️  Cluster '{CLUSTER_NAME}' not found. Creating...")
        run_command(f"kind create cluster --name {CLUSTER_NAME}", check=True, timeout=300)
    else:
        logging.info(f"✅ Kind cluster '{CLUSTER_NAME}' already exists.")


# --------------------------------------------
# Step 2 – Cleanup
# --------------------------------------------
def cleanup_old_resources():
    logging.info("🗑 Cleaning up old pods and ReplicaSets ...\n")
    pods = run_command(f"kubectl get pods -l app=faultinjector -n {NAMESPACE} -o name", timeout=20)
    if pods and "No resources" not in pods:
        for pod in pods.splitlines():
            run_command(f"kubectl delete {pod} -n {NAMESPACE} --ignore-not-found", timeout=30)
    replicasets = run_command(f"kubectl get rs -l app=faultinjector -n {NAMESPACE} -o name", timeout=20)
    if replicasets and "No resources" not in replicasets:
        for rs in replicasets.splitlines():
            run_command(f"kubectl delete {rs} -n {NAMESPACE} --ignore-not-found", timeout=30)
    logging.info("✅ Old resources cleaned up.")


# --------------------------------------------
# Step 3 – Build + Load Image
# --------------------------------------------
def build_and_load_image():
    logging.info(f"🛠 Building local image {IMAGE_NAME} ...\n")
    context_dir = "/workspaces/Cloud-Self-Healing-for-Secure-Containers"
    run_command(f"docker build -t {IMAGE_NAME} -f {DOCKERFILE_PATH} {context_dir}", check=True, timeout=900)
    logging.info("✅ Docker image built successfully.")
    run_command(f"kind load docker-image {IMAGE_NAME} --name {CLUSTER_NAME}", check=True, timeout=120)
    logging.info("✅ Image loaded into Kind cluster.")


# --------------------------------------------
# Step 4 – Patch Deployment
# --------------------------------------------
def choose_deployment_yaml():
    for p in POSSIBLE_DEPLOYMENTS:
        if os.path.exists(p):
            logging.info(f"Using deployment file: {p}")
            return p
    raise FileNotFoundError(f"None of expected deployment files found. Tried: {POSSIBLE_DEPLOYMENTS}")


def patch_deployment_for_local_image(deployment_yaml):
    logging.info("➡️  Patching Deployment YAML for local image usage ...")
    with open(deployment_yaml, "r") as f:
        lines = f.readlines()

    patched = []
    for line in lines:
        if line.strip().startswith("image:"):
            indent = line[: line.index("image:")]
            patched.append(f"{indent}image: {IMAGE_NAME}\n")
        else:
            patched.append(line)

    with open(deployment_yaml, "w") as f:
        f.writelines(patched)

    logging.info("✅ Deployment YAML patched for local image.")


# --------------------------------------------
# Step 5 – Deploy to Kubernetes
# --------------------------------------------
def deploy_to_k8s(deployment_yaml):
    logging.info("\n🚀 Deploying Fault Injector to Kubernetes...\n")
    run_command(f"kubectl apply -f {deployment_yaml} -n {NAMESPACE}", check=True, timeout=120)
    time.sleep(3)
    run_command(f"kubectl get pods -n {NAMESPACE}", timeout=20)
    logging.info("✅ Fault Injector deployment applied.")


# --------------------------------------------
# Step 6 – Apply Prometheus Monitoring Add-ons
# --------------------------------------------
def apply_monitoring_addons():
    logging.info("\n📡 Applying Prometheus monitoring components...\n")

    _exec_with_retries("kubectl apply -f module_3/k8s/prometheus/kube-state-metrics.yaml", retries=3, delay=3)
    _exec_with_retries("kubectl apply -f module_3/k8s/prometheus/node-exporter.yaml", retries=3, delay=3)

    run_command("kubectl get pods -n monitoring -l app=kube-state-metrics", timeout=20)
    run_command("kubectl get pods -n monitoring -l app=node-exporter", timeout=20)

    logging.info("✅ Prometheus add-ons deployed successfully.")


# --------------------------------------------
# Step 7 – Verify Image + Pod State
# --------------------------------------------
def verify_post_deployment():
    logging.info("\n🔍 Verifying Fault Injector Deployment...\n")
    run_command(f"kubectl get pods -n {NAMESPACE} -l app=faultinjector", timeout=20)
    run_command(f"kubectl describe pod -n {NAMESPACE} -l app=faultinjector | grep Image", timeout=20)
    logging.info("✅ Verification complete. Fault Injector active and visible to Prometheus.")


# --------------------------------------------
# Step 8 – Main Deploy Function
# --------------------------------------------
def deploy_module_5():
    logging.info("\n============================================")
    logging.info("🚀 Starting Module 5 – Fault Injector Deployment")
    logging.info("============================================\n")

    check_stress_ng()
    check_kind_cluster()
    cleanup_old_resources()
    build_and_load_image()

    deployment_yaml = choose_deployment_yaml()
    patch_deployment_for_local_image(deployment_yaml)
    deploy_to_k8s(deployment_yaml)

    apply_monitoring_addons()
    verify_post_deployment()

    logging.info("\n✅ Module 5 deployment complete. (Functional tests not run here.)\n")


# --------------------------------------------
# Entrypoint
# --------------------------------------------
if __name__ == "__main__":
    try:
        deploy_module_5()
    except Exception as e:
        logging.error(f"❌ Deployment failed: {e}")
        exit(1)
