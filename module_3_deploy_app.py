# module_3_deploy_app.py
import subprocess
import sys
import time
import requests

K8S_NAMESPACE = "monitoring"
PROM_DEPLOYMENT = "prometheus"
ALERT_DEPLOYMENT = "alertmanager"
PROM_SERVICE = "prometheus"
ALERT_SERVICE = "alertmanager"
POD_READY_TIMEOUT = 180
VERIFY_TIMEOUT = 60  # seconds for endpoint verification

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

def wait_for_pods_ready(label_selector, namespace, timeout=180):
    """Wait until all pods with label_selector are ready."""
    print(f"⏳ Waiting for pods with label '{label_selector}' to be ready...")
    elapsed = 0
    interval = 5
    while elapsed < timeout:
        result = subprocess.run(
            f"kubectl get pods -l {label_selector} -n {namespace} "
            "-o jsonpath='{.items[*].status.containerStatuses[*].ready}'",
            shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        output = result.stdout.strip()
        if output:
            statuses = output.split()
            if all(s == 'true' for s in statuses) and statuses:
                print(f"✅ All {len(statuses)} pods are ready!")
                return True
        time.sleep(interval)
        elapsed += interval
    print(f"⚠ Timeout reached. Pods may not be fully ready: {output}")
    return False

def verify_service(service_name, port, timeout=60):
    """Verify that a service endpoint is reachable via port-forward."""
    print(f"⏳ Verifying {service_name} endpoint on port {port}...")
    pf_cmd = f"kubectl port-forward svc/{service_name} {port}:{port} -n {K8S_NAMESPACE}"
    pf_proc = subprocess.Popen(pf_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(3)

    success = False
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(f"http://127.0.0.1:{port}/")
            if r.status_code == 200:
                success = True
                break
        except requests.exceptions.RequestException:
            time.sleep(2)

    pf_proc.terminate()
    if success:
        print(f"✅ Service {service_name} is reachable!")
    else:
        print(f"⚠ Failed to verify service {service_name}.")
        sys.exit(1)

def deploy_module_3():
    """Deploy Prometheus and Alertmanager with namespace, secrets, and configs."""
    print("=== Module 3 Deployment: Monitoring & Alerts ===")
    
    # Create namespace
    run_command(f"kubectl apply -f module_3/k8s/namespace.yaml")

    # Apply Alertmanager secrets first
    run_command(f"kubectl apply -f module_3/k8s/alertmanager/secret.yaml")

    # Apply ConfigMaps
    run_command(f"kubectl apply -f module_3/k8s/prometheus/configmap.yaml")
    run_command(f"kubectl apply -f module_3/k8s/alertmanager/configmap.yaml")

    # Apply Deployments and Services
    run_command(f"kubectl apply -f module_3/k8s/prometheus/deployment.yaml")
    run_command(f"kubectl apply -f module_3/k8s/prometheus/service.yaml")
    run_command(f"kubectl apply -f module_3/k8s/alertmanager/deployment.yaml")
    run_command(f"kubectl apply -f module_3/k8s/alertmanager/service.yaml")

    # Wait for pods to be ready
    wait_for_pods_ready(f"app={PROM_DEPLOYMENT}", K8S_NAMESPACE, timeout=POD_READY_TIMEOUT)
    wait_for_pods_ready(f"app={ALERT_DEPLOYMENT}", K8S_NAMESPACE, timeout=POD_READY_TIMEOUT)

    # Verify endpoints
    verify_service(PROM_SERVICE, port=9090, timeout=VERIFY_TIMEOUT)
    verify_service(ALERT_SERVICE, port=9093, timeout=VERIFY_TIMEOUT)

    # Show final pod/service status
    run_command(f"kubectl get pods,svc -n {K8S_NAMESPACE}")
    print("\n✅ Module 3 deployment complete! Monitoring and alerts are live.")

if __name__ == "__main__":
    deploy_module_3()
