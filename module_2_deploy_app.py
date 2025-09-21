# module_2_deploy_app.py
import subprocess
import sys
import time
import requests

K8S_NAMESPACE = "default"
DEPLOYMENT_NAME = "module-2-sample-app"
SERVICE_NAME = "module-2-sample-app-service"
DOCKER_IMAGE = "module-2-sample-app:latest"
KIND_CLUSTER = "selfhealing-cluster"
POD_READY_TIMEOUT = 120  # seconds
SERVICE_PORT = 8000
VERIFY_TIMEOUT = 60  # seconds to wait for endpoints

def run_command(cmd, check=True):
    """Run a shell command and print output."""
    try:
        print(f"Running: {cmd}")
        result = subprocess.run(cmd, shell=True, check=check,
                                text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running command:\n{e.output}")
        if check:
            sys.exit(1)
        return False

def wait_for_pods_ready(deployment, namespace, timeout=120):
    """Wait until all pods in a deployment are ready."""
    print(f"⏳ Waiting for pods in deployment '{deployment}' to be ready...")
    elapsed = 0
    interval = 5
    while elapsed < timeout:
        result = subprocess.run(
            f"kubectl get deployment {deployment} -n {namespace} -o jsonpath='{{.status.readyReplicas}}/{{.status.replicas}}'",
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
    print("⏳ Printing pod descriptions for debugging:")
    run_command(f"kubectl describe pods -l app={deployment} -n {namespace}", check=False)
    return False

def print_first_pod_logs(deployment, namespace):
    """Print logs of the first pod in the deployment."""
    result = subprocess.run(
        f"kubectl get pods -l app={deployment} -n {namespace} -o jsonpath='{{.items[0].metadata.name}}'",
        shell=True, text=True, stdout=subprocess.PIPE
    )
    pod_name = result.stdout.strip()
    if pod_name:
        print(f"📄 Logs from pod {pod_name}:")
        run_command(f"kubectl logs {pod_name} -n {namespace}", check=False)

def verify_endpoints(service_name, namespace, port=8000, timeout=60):
    """Verify / and /metrics endpoints are reachable from within cluster using port-forward."""
    print("⏳ Verifying app endpoints (/ and /metrics)...")
    # Start port-forward in background
    pf_cmd = f"kubectl port-forward svc/{service_name} {port}:{port} -n {namespace}"
    pf_proc = subprocess.Popen(pf_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(3)  # wait a few seconds for port-forward to start

    success_root = False
    success_metrics = False
    start = time.time()

    while time.time() - start < timeout:
        try:
            r_root = requests.get(f"http://127.0.0.1:{port}/")
            r_metrics = requests.get(f"http://127.0.0.1:{port}/metrics")
            if r_root.status_code == 200:
                success_root = True
            if r_metrics.status_code == 200:
                success_metrics = True
            if success_root and success_metrics:
                break
        except requests.exceptions.RequestException:
            time.sleep(2)

    pf_proc.terminate()
    if success_root and success_metrics:
        print("✅ Endpoints / and /metrics are reachable!")
    else:
        print("⚠ Failed to verify one or both endpoints.")
        sys.exit(1)

def deploy_module_2_app():
    """Build Docker image, load into Kind, and apply K8s manifests."""
    run_command(f"docker build -t {DOCKER_IMAGE} ./module_2/app")
    run_command(f"kind load docker-image {DOCKER_IMAGE} --name {KIND_CLUSTER}")
    run_command("kubectl apply -f module_2/k8s/deployment.yaml")
    run_command("kubectl apply -f module_2/k8s/service.yaml")

    if wait_for_pods_ready(DEPLOYMENT_NAME, K8S_NAMESPACE, timeout=POD_READY_TIMEOUT):
        print_first_pod_logs(DEPLOYMENT_NAME, K8S_NAMESPACE)
        verify_endpoints(SERVICE_NAME, K8S_NAMESPACE, port=SERVICE_PORT, timeout=VERIFY_TIMEOUT)

    run_command(f"kubectl get pods,svc -n {K8S_NAMESPACE}")
    print("\n✅ Module 2 app deployment complete and fully verified!")

if __name__ == "__main__":
    deploy_module_2_app()
