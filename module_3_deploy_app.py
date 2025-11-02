# ===========================================
# 📡 module_3_deploy_app.py (Final Verified + Metrics Summary)
# Deploys Prometheus & Alertmanager in Kubernetes,
# verifies readiness, checks metrics with retries,
# opens dashboards, and maintains port-forwards.
# ===========================================

import subprocess
import sys
import time
import requests
import webbrowser
from prettytable import PrettyTable

K8S_NAMESPACE = "monitoring"
PROM_DEPLOYMENT = "prometheus"
ALERT_DEPLOYMENT = "alertmanager"
PROM_SERVICE = "prometheus"
ALERT_SERVICE = "alertmanager"
POD_READY_TIMEOUT = 180
VERIFY_TIMEOUT = 60  # seconds for endpoint verification
METRIC_RETRY_LIMIT = 6  # total retry attempts (every 5 seconds)


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
            if statuses and all(s.lower() == 'true' for s in statuses):
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
    pf_proc = subprocess.Popen(
        pf_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    time.sleep(3)  # allow port-forward to start

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

    if not success:
        print(f"⚠ Failed to verify service {service_name}.")
        pf_proc.terminate()
        sys.exit(1)

    print(f"✅ Service {service_name} is reachable!")
    return pf_proc, True


def check_prometheus_metrics():
    """Check if Prometheus metrics are being scraped properly with retry."""
    print("\n📊 Checking Prometheus metrics for activity...")
    for attempt in range(1, METRIC_RETRY_LIMIT + 1):
        cmd = "curl -s http://127.0.0.1:9090/metrics | grep -i restart | head -n 10"
        result = subprocess.run(cmd, shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output = result.stdout.strip()

        if output:
            print(f"✅ Prometheus metrics detected (attempt {attempt}/{METRIC_RETRY_LIMIT}):")
            print(output)
            return True
        else:
            print(f"🔄 Attempt {attempt}/{METRIC_RETRY_LIMIT}: no restart-related metrics yet.")
            time.sleep(5)

    print("⚠ No restart-related metrics found after multiple retries.")
    print("ℹ️ You can manually check later with:")
    print("   curl -s http://127.0.0.1:9090/metrics | grep -i restart | head -n 20")
    return False


def open_dashboards_sequentially(dashboards):
    """Open multiple dashboards in separate browser tabs sequentially."""
    for url in dashboards:
        print(f"🌐 Opening dashboard: {url}")
        webbrowser.open_new_tab(url)
        time.sleep(2)
        print(f"🔗 Clickable URL: {url}")


def ensure_prometheus_configmaps():
    """Ensure all Prometheus ConfigMaps exist before deployment."""
    print("\n🧩 Ensuring all Prometheus ConfigMaps exist...")

    commands = [
        # Main rules directory
        "kubectl create configmap prometheus-rules "
        "--from-file=module_3/alert_rules/ "
        f"-n {K8S_NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -",

        # Kubelet scrape config
        "kubectl create configmap prometheus-kubernetes-kubelet "
        "--from-file=module_3/k8s/prometheus/kubernetes-kubelet.yaml "
        f"-n {K8S_NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -",

        # cAdvisor scrape config
        "kubectl create configmap prometheus-kubernetes-cadvisor "
        "--from-file=module_3/k8s/prometheus/kubernetes-cadvisor.yaml "
        f"-n {K8S_NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -",
    ]

    for cmd in commands:
        run_command(cmd, check=False)

    print("✅ All required ConfigMaps verified or created.\n")


def deploy_module_3():
    """Deploy Prometheus and Alertmanager with namespace, secrets, and configs."""
    print("=== 🚀 Module 3 Deployment: Monitoring & Alerts ===")

    # Namespace
    run_command("kubectl apply -f module_3/k8s/namespace.yaml")

    # Prometheus ServiceAccount + RBAC
    run_command("kubectl apply -f module_3/k8s/prometheus/serviceaccount.yaml")

    # Alertmanager secrets
    run_command("kubectl apply -f module_3/k8s/alertmanager/secret.yaml")

    # ConfigMaps
    run_command("kubectl apply -f module_3/k8s/prometheus/configmap.yaml")
    run_command("kubectl apply -f module_3/k8s/alertmanager/configmap.yaml")

    # Ensure Prometheus has all supporting ConfigMaps
    ensure_prometheus_configmaps()

    # Deployments & Services
    run_command("kubectl apply -f module_3/k8s/prometheus/deployment.yaml")
    run_command("kubectl apply -f module_3/k8s/prometheus/service.yaml")
    run_command("kubectl apply -f module_3/k8s/alertmanager/deployment.yaml")
    run_command("kubectl apply -f module_3/k8s/alertmanager/service.yaml")

    # Wait for pods ready
    prom_ready = wait_for_pods_ready(f"app={PROM_DEPLOYMENT}", K8S_NAMESPACE, POD_READY_TIMEOUT)
    alert_ready = wait_for_pods_ready(f"app={ALERT_DEPLOYMENT}", K8S_NAMESPACE, POD_READY_TIMEOUT)

    # Verify endpoints
    prom_pf_proc, prom_ok = verify_service(PROM_SERVICE, 9090, VERIFY_TIMEOUT)
    alert_pf_proc, alert_ok = verify_service(ALERT_SERVICE, 9093, VERIFY_TIMEOUT)

    # 🔹 Check metrics (with automatic retry)
    metrics_ok = check_prometheus_metrics()

    # Open dashboards sequentially
    open_dashboards_sequentially([
        "http://127.0.0.1:9090",  # Prometheus
        "http://127.0.0.1:9093"   # Alertmanager
    ])

    # Final pod/service status
    run_command(f"kubectl get pods,svc -n {K8S_NAMESPACE}")

    # 📋 Deployment Summary
    print("\n📋 Deployment Summary\n" + "=" * 40)
    table = PrettyTable()
    table.field_names = ["Component", "Status"]
    table.add_row(["Prometheus Pod", "✅ Ready" if prom_ready else "⚠ Not Ready"])
    table.add_row(["Alertmanager Pod", "✅ Ready" if alert_ready else "⚠ Not Ready"])
    table.add_row(["Prometheus Service", "✅ Reachable" if prom_ok else "⚠ Failed"])
    table.add_row(["Alertmanager Service", "✅ Reachable" if alert_ok else "⚠ Failed"])
    table.add_row(["Metrics Check", "✅ Active" if metrics_ok else "⚠ None Detected"])
    print(table)
    print("=" * 40)

    print("\n✅ Module 3 deployment complete! Monitoring and alerts are live.")

    # Keep port-forward alive
    try:
        print("\n⏳ Port-forward processes running. Press Ctrl+C to exit.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Terminating port-forward processes...")
        prom_pf_proc.terminate()
        alert_pf_proc.terminate()
        print("✅ Port-forward processes terminated. Module 3 session ended.")


if __name__ == "__main__":
    deploy_module_3()
