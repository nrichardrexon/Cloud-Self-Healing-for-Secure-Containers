# module_4_deploy_app.py
import subprocess
import os
import sys
from pathlib import Path
import yaml
import time
import json

LOCAL_IMAGE = "remediator:latest"
MODULE_DIR = Path(__file__).parent / "module_4"
DEPLOYMENT_YAML = MODULE_DIR / "k8s" / "deployment.yaml"
NAMESPACE = "monitoring"
LABEL_SELECTOR = "app=remediator"
KIND_CLUSTER_NAME = "selfhealing-cluster"

def run_command(cmd):
    print(f"Running: {cmd}")
    try:
        result = subprocess.run(
            cmd, shell=True, check=True, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        print(result.stdout)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error running command:\n{e.output}")
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
    """Load local Docker image into Kind cluster to avoid pull errors."""
    print(f"Loading local image {LOCAL_IMAGE} into Kind cluster...")
    run_command(f"kind load docker-image {LOCAL_IMAGE} --name {KIND_CLUSTER_NAME}")
    print("✅ Image loaded into Kind cluster.")

# ========================
# Deployment helpers
# ========================
def cleanup_old_resources():
    print("🗑 Cleaning up old Remediator pods and ReplicaSets...")
    pods_output = run_command(f"kubectl get pods -l {LABEL_SELECTOR} -n {NAMESPACE} -o name")
    pods = pods_output.splitlines() if pods_output else []
    for pod in pods:
        run_command(f"kubectl delete {pod} -n {NAMESPACE}")

    rs_output = run_command(f"kubectl get rs -l {LABEL_SELECTOR} -n {NAMESPACE} -o name")
    replicasets = rs_output.splitlines() if rs_output else []
    for rs in replicasets:
        run_command(f"kubectl delete {rs} -n {NAMESPACE}")

def build_local_image():
    print("🛠 Building local image remediator:latest...")
    run_command(f"docker build -t {LOCAL_IMAGE} {MODULE_DIR}")

def patch_deployment_for_local_image():
    print("➡ Patching Deployment YAML for local image usage...")
    with open(DEPLOYMENT_YAML, "r") as f:
        deployment = yaml.safe_load(f)

    containers = deployment["spec"]["template"]["spec"]["containers"]
    for container in containers:
        container["image"] = LOCAL_IMAGE
        container["imagePullPolicy"] = "IfNotPresent"

    with open(DEPLOYMENT_YAML, "w") as f:
        yaml.safe_dump(deployment, f)

    print("✅ Deployment YAML patched.")

def apply_k8s_resources():
    for resource in ["configmap.yaml", "deployment.yaml", "service.yaml"]:
        run_command(f"kubectl apply -f {MODULE_DIR / 'k8s' / resource}")

def wait_for_pods(label=LABEL_SELECTOR, namespace=NAMESPACE, interval=5):
    """Wait until all pods are ready, streaming events for debugging."""
    last_timestamp = ""
    while True:
        pods_status = run_command(
            f"kubectl get pods -l {label} -n {namespace} "
            "-o jsonpath='{.items[*].status.containerStatuses[*].ready}'"
        ).strip().replace("'", "")
        if pods_status:
            status_list = pods_status.split()
            print(f"Pods readiness: {status_list}")
            if all(s.lower() == "true" for s in status_list):
                print("✅ All pods are ready!")
                break
        else:
            print("Pods not yet created...")

        # Show recent events
        events_json = run_command(
            f"kubectl get events -n {namespace} --sort-by='.lastTimestamp' -o json"
        )
        try:
            events = json.loads(events_json)
            for e in events.get("items", []):
                ts = e["metadata"]["creationTimestamp"]
                if ts > last_timestamp:
                    last_timestamp = ts
                    msg = e["message"]
                    typ = e["type"]
                    reason = e.get("reason", "")
                    obj = e["involvedObject"].get("name", "")
                    print(f"[{ts}] {typ}/{reason} -> {obj}: {msg}")
        except json.JSONDecodeError:
            pass

        print(f"⏳ Pods not ready yet. Retrying in {interval}s...")
        time.sleep(interval)

# ========================
# Main deployment flow
# ========================
def deploy_module_4():
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
    deploy_module_4()
