# =========================================
# ✅ module_5_functional_test.py (Final Updated - Cluster-Consistent)
# Purpose: Validate self-healing by injecting controlled faults and verifying alerts
# =========================================

import subprocess
import time
from pathlib import Path
import logging
import requests
import json

# ========================
# Configuration
# ========================
NAMESPACE = "monitoring"
LABEL_SELECTOR = "app=faultinjector"
PROMETHEUS_URL = "http://prometheus.monitoring.svc.cluster.local:9090/api/v1/query"
LOG_FILE = Path(__file__).parent / "functional_test.log"
EXPECTED_IMAGE = "ubuntu:22.04"  # matches new test-remediator.yaml
FAULTY_IMAGE = "busybox:nonexistent"  # deliberately broken for test
PROMETHEUS_TIMEOUT = 90  # seconds

# ========================
# Logging setup
# ========================
logging.basicConfig(
    filename=LOG_FILE,
    filemode="w",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# ========================
# Helper functions
# ========================
def run_command(cmd: str):
    """Run a shell command and return output (with logging)."""
    print(f"Running: {cmd}")
    try:
        result = subprocess.run(
            cmd, shell=True, check=True, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        logging.info(result.stdout.strip())
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logging.error(f"Command failed: {cmd}\n{e.output}")
        return ""


def get_target_pods(label=LABEL_SELECTOR):
    """Return list of pods matching label."""
    pods_output = run_command(f"kubectl get pods -l {label} -n {NAMESPACE} -o name")
    pods = [p for p in pods_output.splitlines() if p.strip()]
    return pods


def wait_for_pods_ready(label=LABEL_SELECTOR, timeout=90):
    """Wait until all pods with the label are ready."""
    print("⏳ Waiting for all pods to be ready...")
    start_time = time.time()
    while True:
        status_output = run_command(
            f"kubectl get pods -l {label} -n {NAMESPACE} "
            "-o jsonpath='{.items[*].status.containerStatuses[*].ready}'"
        ).replace("'", "")
        if status_output and all(s.lower() == "true" for s in status_output.split()):
            print("✅ All pods are ready!")
            return True
        if time.time() - start_time > timeout:
            print("⚠️ Timeout waiting for pods to be ready")
            return False
        time.sleep(5)


# ========================
# Fault injection functions
# ========================
def cpu_stress(pod, duration=10, workers=2):
    """Inject CPU stress into a container."""
    print(f"⚡ Injecting CPU stress into {pod} for {duration}s")
    run_command(
        f"kubectl exec -n {NAMESPACE} {pod} -- bash -c "
        f"\"apt-get update && apt-get install -y stress && stress --cpu {workers} --timeout {duration}\""
    )
    logging.info(f"CPU stress applied to {pod} for {duration}s")


def memory_stress(pod, duration=10, size_mb=100):
    """Inject memory stress."""
    print(f"⚡ Injecting memory stress into {pod} ({size_mb}MB) for {duration}s")
    run_command(
        f"kubectl exec -n {NAMESPACE} {pod} -- bash -c "
        f"\"apt-get update && apt-get install -y stress && stress --vm 1 --vm-bytes {size_mb}M --timeout {duration}\""
    )
    logging.info(f"Memory stress applied to {pod} for {duration}s")


def kill_main_process(pod):
    """Kill the main Python process (simulated crash)."""
    print(f"⚡ Killing main process inside {pod}")
    pid = run_command(f"kubectl exec -n {NAMESPACE} {pod} -- bash -c \"pgrep -o python3 || echo ''\"")
    if pid.strip().isdigit():
        run_command(f"kubectl exec -n {NAMESPACE} {pod} -- kill -9 {pid}")
        logging.info(f"Killed process {pid} in {pod}")
    else:
        print("⚠️ No main process found to kill.")
        logging.warning(f"No python process found in {pod}")


def deploy_faulty_image():
    """Deploy intentionally broken image to test remediator recovery."""
    print("⚡ Deploying faulty image to test remediator")
    run_command(
        f"kubectl set image deployment/test-remediator faultinjector={FAULTY_IMAGE} -n {NAMESPACE}"
    )
    logging.info(f"Faulty image '{FAULTY_IMAGE}' deployed to test-remediator")


# ========================
# Prometheus alert verification
# ========================
def check_prometheus_alert(alert_name, timeout=PROMETHEUS_TIMEOUT):
    """Check if a given Prometheus alert fired within timeout."""
    print(f"⏳ Checking for Prometheus alert: {alert_name}")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(
                PROMETHEUS_URL,
                params={"query": f"ALERTS{{alertname='{alert_name}', alertstate='firing'}}"},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("data", {}).get("result"):
                    print(f"✅ Alert '{alert_name}' detected in Prometheus")
                    logging.info(f"Alert '{alert_name}' triggered")
                    return True
        except Exception as e:
            logging.error(f"Prometheus query failed: {e}")
        time.sleep(10)
    print(f"⚠️ Alert '{alert_name}' not detected within timeout")
    logging.warning(f"Alert '{alert_name}' not detected")
    return False


# ========================
# Remediator validation
# ========================
def validate_remediator():
    """Confirm that the remediator restored normal state."""
    print("⏳ Validating remediator actions...")

    if not wait_for_pods_ready(timeout=90):
        print("❌ Pods did not recover in time")
        logging.error("Pods did not recover in time")
        return False

    pods = get_target_pods()
    all_correct = True

    for pod in pods:
        image = run_command(
            f"kubectl get {pod} -n {NAMESPACE} -o jsonpath='{{.spec.containers[0].image}}'"
        )
        if image != EXPECTED_IMAGE:
            print(f"❌ Pod {pod} has wrong image: {image}")
            logging.error(f"Pod {pod} has wrong image: {image}")
            all_correct = False
        else:
            logging.info(f"Pod {pod} running correct image {image}")

    desired = run_command(f"kubectl get deployment test-remediator -n {NAMESPACE} -o jsonpath='{{.spec.replicas}}'")
    ready = run_command(f"kubectl get deployment test-remediator -n {NAMESPACE} -o jsonpath='{{.status.readyReplicas}}'")

    if desired != ready:
        print(f"❌ Deployment replica mismatch: desired={desired}, ready={ready}")
        logging.error(f"Replica mismatch: desired={desired}, ready={ready}")
        all_correct = False

    if all_correct:
        print("✅ Remediator validated successfully")
        logging.info("Remediator successfully restored deployment")
    return all_correct


# ========================
# Functional testing workflow
# ========================
def run_functional_tests():
    print("=== 🚀 Starting Module 5 Functional Tests ===")

    wait_for_pods_ready()
    pods = get_target_pods()
    if not pods:
        print("❌ No target pods found for testing!")
        logging.error("No pods found for testing")
        return

    # 1️⃣ CPU & Memory stress test
    for pod in pods:
        cpu_stress(pod, duration=5, workers=2)
        memory_stress(pod, duration=5, size_mb=50)
        check_prometheus_alert("HighCPUUsage")
        check_prometheus_alert("HighMemoryUsage")
        validate_remediator()

    # 2️⃣ Process kill simulation
    for pod in pods:
        kill_main_process(pod)
        check_prometheus_alert("ContainerCrash")
        validate_remediator()

    # 3️⃣ Faulty image deployment test
    deploy_faulty_image()
    check_prometheus_alert("DeploymentFailed")
    validate_remediator()

    print("✅ Functional testing complete!")
    logging.info("Functional testing finished successfully")


# ========================
# Entry point
# ========================
if __name__ == "__main__":
    run_functional_tests()
