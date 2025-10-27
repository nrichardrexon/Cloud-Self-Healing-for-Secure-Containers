# ============================================
# module_4_deploy_app.py – Kind + Prometheus-safe Remediator Deployment (Final)
# ============================================
import subprocess
import os
import sys
import time
import yaml
import requests
import signal
from pathlib import Path

# -----------------------
# Config
# -----------------------
LOCAL_IMAGE = "remediator:latest"
MODULE_DIR = Path(__file__).parent / "module_4"
K8S_DIR = MODULE_DIR / "k8s"
DEPLOYMENT_YAML = K8S_DIR / "deployment.yaml"
NAMESPACE = "monitoring"
LABEL_SELECTOR = "app=remediator"
KIND_CLUSTER_NAME = "selfhealing-cluster"
SERVICE_NAME = "remediator"
METRICS_PATH = "/metrics"
HEALTH_PATH = "/health"
PORT = 8080


# -----------------------
# Shell Helper
# -----------------------
def run_command(cmd, exit_on_fail=False):
    print(f"⚙️  Running: {cmd}")
    try:
        result = subprocess.run(
            cmd, shell=True, check=True, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        print(result.stdout)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"⚠️  Error running command:\n{e.output}")
        if exit_on_fail:
            sys.exit(1)
        return ""


# -----------------------
# Kind Helpers
# -----------------------
def is_kind_installed():
    try:
        run_command("kind --version")
        return True
    except Exception:
        return False


def install_kind():
    print("⬇ Installing Kind in ~/bin ...")
    run_command("mkdir -p ~/bin")
    run_command("curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.25.0/kind-linux-amd64")
    run_command("chmod +x ./kind && mv ./kind ~/bin/")
    os.environ["PATH"] = f"{os.path.expanduser('~/bin')}:" + os.environ["PATH"]
    print("✅ Kind installed.")


def create_kind_cluster():
    clusters = run_command("kind get clusters").splitlines()
    if KIND_CLUSTER_NAME in clusters:
        print(f"✅ Kind cluster '{KIND_CLUSTER_NAME}' already exists.")
        return
    print(f"🌱 Creating Kind cluster '{KIND_CLUSTER_NAME}'...")
    run_command(f"kind create cluster --name {KIND_CLUSTER_NAME} --wait 90s")
    print("✅ Kind cluster ready.")


# -----------------------
# Kubernetes Helpers
# -----------------------
def ensure_namespace():
    """Create monitoring namespace if missing."""
    print(f"📁 Ensuring namespace '{NAMESPACE}' exists...")
    namespaces = run_command("kubectl get ns -o name")
    if f"namespace/{NAMESPACE}" not in namespaces:
        run_command(f"kubectl create ns {NAMESPACE}")
        print(f"✅ Namespace '{NAMESPACE}' created.")
    else:
        print(f"✅ Namespace '{NAMESPACE}' already exists.")


def cleanup_old_resources():
    """Remove old pods/replicasets for clean redeploy."""
    print("🧹 Cleaning up old Remediator pods and ReplicaSets...")
    run_command(f"kubectl delete pods -l {LABEL_SELECTOR} -n {NAMESPACE} --ignore-not-found")
    run_command(f"kubectl delete rs -l {LABEL_SELECTOR} -n {NAMESPACE} --ignore-not-found")


def build_local_image():
    """Build fresh local image."""
    print("🛠 Building local Remediator image...")
    run_command(f"docker build -t {LOCAL_IMAGE} {MODULE_DIR}")
    print("✅ Docker image built.")


def load_image_into_kind():
    """Load image into Kind cluster."""
    print(f"📦 Loading local image {LOCAL_IMAGE} into Kind cluster...")
    run_command(f"kind load docker-image {LOCAL_IMAGE} --name {KIND_CLUSTER_NAME}")
    print("✅ Image loaded into Kind cluster.")


def patch_deployment_for_local_image():
    """Patch Deployment YAML to use local image without pulling."""
    print("🧩 Patching Deployment YAML for local image...")
    with open(DEPLOYMENT_YAML, "r") as f:
        deployment = yaml.safe_load(f)

    for container in deployment["spec"]["template"]["spec"]["containers"]:
        container["image"] = LOCAL_IMAGE
        container["imagePullPolicy"] = "IfNotPresent"

    with open(DEPLOYMENT_YAML, "w") as f:
        yaml.safe_dump(deployment, f)
    print("✅ Deployment YAML patched successfully.")


def apply_k8s_resources():
    """Apply ConfigMap, Deployment, and Service for Remediator."""
    print("🚀 Applying Remediator Kubernetes resources...")
    ensure_namespace()
    for resource in ["configmap.yaml", "deployment.yaml", "service.yaml"]:
        resource_path = K8S_DIR / resource
        if not resource_path.exists():
            print(f"⚠️  Missing: {resource_path}")
            continue
        run_command(f"kubectl apply -f {resource_path} -n {NAMESPACE}")
    print("✅ All K8s resources applied.")


def wait_for_pods(label=LABEL_SELECTOR, namespace=NAMESPACE, interval=5, timeout=180):
    """Wait until Remediator pods are ready."""
    print("⏳ Waiting for Remediator pods to be ready...")
    start = time.time()
    while True:
        status = run_command(
            f"kubectl get pods -l {label} -n {namespace} "
            "-o jsonpath='{.items[*].status.containerStatuses[*].ready}'"
        ).strip().replace("'", "")
        if status:
            states = status.split()
            print(f"Pods readiness: {states}")
            if all(s.lower() == "true" for s in states):
                print("✅ All pods are ready!")
                return True
        if time.time() - start > timeout:
            print("⚠️  Timeout waiting for pods to become ready.")
            return False
        time.sleep(interval)


# -----------------------
# Verification
# -----------------------
def verify_metrics_endpoint():
    """Verify if /metrics and /health endpoints respond correctly."""
    print("🔎 Verifying /metrics and /health endpoints...")

    port_forward = subprocess.Popen(
        ["kubectl", "port-forward", f"svc/{SERVICE_NAME}", f"{PORT}:{PORT}", "-n", NAMESPACE],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setsid
    )
    time.sleep(4)  # Give port-forward time to initialize

    try:
        for endpoint in [HEALTH_PATH, METRICS_PATH]:
            url = f"http://127.0.0.1:{PORT}{endpoint}"
            print(f"➡ Checking {url}")
            try:
                resp = requests.get(url, timeout=5)
                if resp.status_code == 200:
                    print(f"✅ {endpoint} reachable.")
                elif resp.status_code == 404:
                    print(f"❌ {endpoint} not found (HTTP 404) — check FastAPI setup.")
                else:
                    print(f"⚠️ {endpoint} returned HTTP {resp.status_code}")
            except requests.exceptions.RequestException as e:
                print(f"⚠️ Could not reach {endpoint}: {e}")
                print("💡 Possible cause: container app not listening or port mismatch.")
    finally:
        os.killpg(os.getpgid(port_forward.pid), signal.SIGTERM)
        print("🧯 Port-forward closed.")


# -----------------------
# Main Deployment Entry
# -----------------------
def deploy_module_4():
    if not is_kind_installed():
        install_kind()
    create_kind_cluster()
    cleanup_old_resources()
    build_local_image()
    load_image_into_kind()
    patch_deployment_for_local_image()
    apply_k8s_resources()

    if wait_for_pods():
        verify_metrics_endpoint()
        print("🎯 Remediator successfully deployed and verified.")
    else:
        print("❌ Deployment failed — pods not ready or service unreachable.")


if __name__ == "__main__":
    deploy_module_4()
