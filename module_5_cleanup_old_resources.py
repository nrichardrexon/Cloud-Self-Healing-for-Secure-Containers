# module_5_cleanup_old_resources.py
import subprocess
import sys
from pathlib import Path

NAMESPACE = "monitoring"
LABEL_SELECTOR = "app=faultinjector"
DEPLOYMENT_NAME = "test-remediator"

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
        print(f"⚠️ Error running command:\n{e.output}")
        return None

def delete_deployment():
    print(f"🗑 Deleting Deployment {DEPLOYMENT_NAME} in namespace {NAMESPACE}...")
    run_command(f"kubectl delete deployment {DEPLOYMENT_NAME} -n {NAMESPACE} --ignore-not-found")

def delete_pods():
    print(f"🗑 Deleting pods with label {LABEL_SELECTOR} in namespace {NAMESPACE}...")
    pods_output = run_command(f"kubectl get pods -l {LABEL_SELECTOR} -n {NAMESPACE} -o name")
    if pods_output:
        pods = pods_output.splitlines()
        for pod in pods:
            run_command(f"kubectl delete {pod} -n {NAMESPACE}")

def delete_replicasets():
    print(f"🗑 Deleting ReplicaSets with label {LABEL_SELECTOR} in namespace {NAMESPACE}...")
    rs_output = run_command(f"kubectl get rs -l {LABEL_SELECTOR} -n {NAMESPACE} -o name")
    if rs_output:
        replicasets = rs_output.splitlines()
        for rs in replicasets:
            run_command(f"kubectl delete {rs} -n {NAMESPACE}")

if __name__ == "__main__":
    delete_deployment()
    delete_pods()
    delete_replicasets()
    print("✅ Module 5 old resources cleanup completed.")
