# module_1_deploy_sample_app.py
import subprocess
import sys
import time
from kubernetes_kind_setup import install_kind, create_cluster

K8S_NAMESPACE = "default"
DEPLOYMENT_NAME = "sample-app-deployment"       # updated
SERVICE_NAME = "sample-app-service"             # updated
DOCKER_IMAGE = "sample-app:latest"              # updated
POD_READY_TIMEOUT = 120  # seconds

def run_command(cmd, check=True):
    """Run a shell command and print output."""
    try:
        print(f"Running: {cmd}")
        result = subprocess.run(
            cmd, shell=True, check=check,
            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running command:\n{e.output}")
        if check:
            sys.exit(1)
        return False

def check_kind_cluster():
    """Check if Kind cluster exists."""
    result = subprocess.run(
        "kind get clusters", shell=True, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    clusters = result.stdout.strip().splitlines()
    if "selfhealing-cluster" in clusters:
        print("✅ Kind cluster found.")
        return True
    else:
        print("⚠ Kind cluster not found. Installing and creating it now...")
        install_kind()
        create_cluster()
        return True

def wait_for_pods_ready(deployment, namespace, timeout=120):
    """Wait until all pods in a deployment are ready."""
    print(f"⏳ Waiting for pods in deployment '{deployment}' to be ready...")
    elapsed = 0
    interval = 5
    while elapsed < timeout:
        result = subprocess.run(
            f"kubectl get deployment {deployment} -n {namespace} "
            f"-o jsonpath='{{.status.readyReplicas}}/{{.status.replicas}}'",
            shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        output = result.stdout.strip()
        if output and '/' in output:
            ready, total = map(lambda x: int(x or 0), output.split('/'))
            if ready == total and total != 0:
                print(f"✅ All {total} pods are ready!")
                return True
        time.sleep(interval)
        elapsed += interval
    print(f"⚠ Timeout reached. Pods may not be fully ready: {output}")
    return False

def deploy_app():
    """Build Docker image, load into Kind, and apply K8s manifests."""
    run_command(f"docker build -t {DOCKER_IMAGE} ./app")
    run_command(f"kind load docker-image {DOCKER_IMAGE} --name selfhealing-cluster")
    run_command("kubectl apply -f k8s/deployment.yaml")
    run_command("kubectl apply -f k8s/service.yaml")
    wait_for_pods_ready(DEPLOYMENT_NAME, K8S_NAMESPACE, timeout=POD_READY_TIMEOUT)
    run_command(f"kubectl get pods,svc -n {K8S_NAMESPACE}")
    print("\n✅ Sample app deployment complete and ready!")

def main():
    check_kind_cluster()
    deploy_app()

if __name__ == "__main__":
    main()
