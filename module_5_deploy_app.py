# module_5_deploy_app.py
import subprocess
import os
import sys
from pathlib import Path
import yaml
import time

LOCAL_IMAGE = "module5-faultinjector:latest"
MODULE_DIR = Path(__file__).parent / "module_5"
DEPLOYMENT_YAML = MODULE_DIR / "k8s" / "test-deployment.yaml"
NAMESPACE = "monitoring"
LABEL_SELECTOR = "app=faultinjector"
KIND_CLUSTER_NAME = "selfhealing-cluster"

def run_command(cmd):
    print(f"Running: {cmd}")
    try:
        result = subprocess.run(
            cmd, shell=True, check=True, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        print(result.stdout)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Command failed:\n{e.output}")
        return ""

# ========================
# Kind helpers
# ========================
def is_kind_installed():
    try:
        run_command("kind --version")
        return True
    except SystemExit:
        return False

def install_kind():
    print("Installing Kind in ~/bin...")
    run_command("mkdir -p ~/bin")
    run_command("curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.25.0/kind-linux-amd64")
    run_command("chmod +x ./kind")
    run_command("mv ./kind ~/bin/")
    bashrc_line = "export PATH=$HOME/bin:$PATH"
    bashrc_path = os.path.expanduser("~/.bashrc")
    with open(bashrc_path, "a") as f:
        f.write(f"\n{bashrc_line}\n")
    os.environ["PATH"] = f"{os.path.expanduser('~/bin')}:" + os.environ["PATH"]
    print("✅ Kind installed. PATH updated.")

def create_kind_cluster():
    clusters = run_command("kind get clusters").splitlines()
    if KIND_CLUSTER_NAME in clusters:
        print("✅ Kind cluster already exists.")
        return
    print(f"Creating Kind cluster '{KIND_CLUSTER_NAME}'...")
    run_command(f"kind create cluster --name {KIND_CLUSTER_NAME} --wait 60s")
    print("✅ Kind cluster ready.")

def load_image_into_kind():
    print(f"Loading local image {LOCAL_IMAGE} into Kind cluster...")
    run_command(f"kind load docker-image {LOCAL_IMAGE} --name {KIND_CLUSTER_NAME}")
    print("✅ Image loaded into Kind cluster.")

# ========================
# Deployment helpers
# ========================
def cleanup_old_resources():
    print("🗑 Cleaning up old pods and ReplicaSets...")
    pods_output = run_command(f"kubectl get pods -l {LABEL_SELECTOR} -n {NAMESPACE} -o name")
    pods = pods_output.splitlines() if pods_output else []
    for pod in pods:
        run_command(f"kubectl delete {pod} -n {NAMESPACE}")

    rs_output = run_command(f"kubectl get rs -l {LABEL_SELECTOR} -n {NAMESPACE} -o name")
    replicasets = rs_output.splitlines() if rs_output else []
    for rs in replicasets:
        run_command(f"kubectl delete {rs} -n {NAMESPACE}")

def build_local_image():
    print(f"🛠 Building local image {LOCAL_IMAGE} with kubectl included...")
    run_command(f"docker build -t {LOCAL_IMAGE} {MODULE_DIR}")

def patch_deployment_for_local_image():
    print("➡ Patching Deployment YAML for local image usage...")
    with open(DEPLOYMENT_YAML, "r") as f:
        deployment_docs = list(yaml.safe_load_all(f))

    # Find the Deployment doc
    for doc in deployment_docs:
        if doc.get("kind") == "Deployment":
            containers = doc["spec"]["template"]["spec"]["containers"]
            for container in containers:
                container["image"] = LOCAL_IMAGE
                container["imagePullPolicy"] = "IfNotPresent"

    with open(DEPLOYMENT_YAML, "w") as f:
        yaml.safe_dump_all(deployment_docs, f)

    print("✅ Deployment YAML patched.")

def apply_k8s_resources():
    run_command(f"kubectl apply -f {DEPLOYMENT_YAML}")

def wait_for_pods(label=LABEL_SELECTOR, namespace=NAMESPACE):
    print("⏳ Waiting for pods to be ready...")
    while True:
        pods_status = run_command(
            f"kubectl get pods -l {label} -n {namespace} "
            "-o jsonpath='{.items[*].status.containerStatuses[*].ready}'"
        )
        if pods_status:
            statuses = pods_status.strip().split()
            if all(s.lower() == "true" for s in statuses):
                print("✅ All pods are ready!")
                break
        print("⏳ Pods not ready yet. Retrying in 5s...")
        time.sleep(5)

# ========================
# Main deployment flow
# ========================
def deploy_module_5():
    if not is_kind_installed():
        install_kind()
    create_kind_cluster()

    cleanup_old_resources()
    build_local_image()
    load_image_into_kind()
    patch_deployment_for_local_image()
    apply_k8s_resources()
    wait_for_pods()

if __name__ == "__main__":
    deploy_module_5()
