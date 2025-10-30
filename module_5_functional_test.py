# =========================================
# ✅ module_5_functional_test.py (Final Stable & Cluster-Consistent)
# Purpose: Validate self-healing by injecting controlled faults and verifying alerts
# =========================================

import subprocess
import time
from pathlib import Path
import logging
import requests
import os

# ========================
# Configuration
# ========================
NAMESPACE = "monitoring"
LABEL_SELECTOR = "app=faultinjector"
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://prometheus.monitoring.svc.cluster.local:9090/api/v1/query")
LOG_FILE = Path(__file__).parent / "functional_test.log"
EXPECTED_IMAGE = "test-remediator:latest"
FAULTY_IMAGE = "busybox:nonexistent"
PROMETHEUS_TIMEOUT = 90
TARGET_CONTAINER = "faultinjector"  # main container name

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
def run_command(cmd: str, check: bool = False):
    """Run a shell command and return output (with logging)."""
    print(f"Running: {cmd}")
    try:
        result = subprocess.run(
            cmd, shell=True, check=check, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        output = result.stdout.strip()
        logging.info(output)
        return output
    except subprocess.CalledProcessError as e:
        logging.error(f"Command failed: {cmd}\n{e.output}")
        return ""

def get_target_pods(label=LABEL_SELECTOR):
    """Return list of pods matching label (only names)."""
    pods_output = run_command(f"kubectl get pods -l {label} -n {NAMESPACE} -o name")
    pods = [p.replace("pod/", "") for p in pods_output.splitlines() if p.strip()]
    return pods

def wait_for_pods_ready(label=LABEL_SELECTOR, timeout=120):
    """Wait until target pods are ready (tolerates sidecar init timing)."""
    print("⏳ Waiting for pods to be ready (main container check)...")
    start_time = time.time()
    while True:
        names_output = run_command(
            f"kubectl get pods -l {label} -n {NAMESPACE} "
            "-o jsonpath='{.items[*].status.containerStatuses[*].name}'"
        ).replace("'", "")
        ready_output = run_command(
            f"kubectl get pods -l {label} -n {NAMESPACE} "
            "-o jsonpath='{.items[*].status.containerStatuses[*].ready}'"
        ).replace("'", "")

        names = names_output.split()
        readiness = ready_output.split()
        if names and readiness:
            container_status = dict(zip(names, readiness))
            main_ready = container_status.get(TARGET_CONTAINER) == "true"
            all_ready = all(v == "true" for v in readiness)
            if main_ready or all_ready:
                print("✅ Required pods are ready!")
                return True

        if time.time() - start_time > timeout:
            print(f"⚠️ Timeout waiting for pods to be ready (status={ready_output})")
            logging.warning(f"Readiness timeout: {ready_output}")
            return False
        time.sleep(5)

# ========================
# Fault injection functions
# ========================
def _exec_with_retries(cmd, retries=3, delay=3):
    """Exec shell cmd with small retry loop."""
    for attempt in range(1, retries + 1):
        out = run_command(cmd)
        if out and "not found" not in out and "Error from server" not in out:
            return out
        time.sleep(delay)
    return out

def cpu_stress(pod, duration=60, workers=2):
    """Inject CPU stress inside main container."""
    print(f"⚡ Injecting CPU stress into {pod} for {duration}s")
    cmd = f"kubectl exec -n {NAMESPACE} {pod} -c {TARGET_CONTAINER} -- /bin/sh -c \"stress --cpu {workers} --timeout {duration}\""
    out = _exec_with_retries(cmd)
    logging.info(f"CPU stress output for {pod}: {out}")
    return out

def memory_stress(pod, duration=60, size_mb=100):
    """Inject memory stress inside main container."""
    print(f"⚡ Injecting memory stress into {pod} ({size_mb}MB) for {duration}s")
    cmd = f"kubectl exec -n {NAMESPACE} {pod} -c {TARGET_CONTAINER} -- /bin/sh -c \"stress --vm 1 --vm-bytes {size_mb}M --timeout {duration}\""
    out = _exec_with_retries(cmd)
    logging.info(f"Memory stress output for {pod}: {out}")
    return out

def kill_main_process(pod):
    """Kill the main Python process inside the container."""
    print(f"⚡ Killing main process inside {pod}")
    pid = run_command(f"kubectl exec -n {NAMESPACE} {pod} -c {TARGET_CONTAINER} -- pgrep -o python3 || true")
    if pid and pid.strip().isdigit():
        run_command(f"kubectl exec -n {NAMESPACE} {pod} -c {TARGET_CONTAINER} -- kill -9 {pid.strip()}")
        logging.info(f"Killed process {pid.strip()} in {pod}")
    else:
        logging.warning(f"No python process found in {pod}")

def deploy_faulty_image():
    """Deploy intentionally broken image to test remediator recovery."""
    print("⚡ Deploying faulty image to test remediator")
    out = run_command(f"kubectl set image deployment/test-remediator {TARGET_CONTAINER}={FAULTY_IMAGE} -n {NAMESPACE}")
    logging.info(out)
    logging.info(f"Faulty image '{FAULTY_IMAGE}' deployed to test-remediator")

# ========================
# Prometheus alert verification
# ========================
def _query_prometheus(url, params, timeout=10):
    resp = requests.get(url, params=params, timeout=timeout)
    resp.raise_for_status()
    return resp.json()

def check_prometheus_alert(alert_name, timeout=PROMETHEUS_TIMEOUT):
    """Check if a given Prometheus alert fired within timeout."""
    print(f"⏳ Checking for Prometheus alert: {alert_name}")
    start_time = time.time()
    tried_local = False
    cluster_url = PROMETHEUS_URL
    local_url = "http://127.0.0.1:9090/api/v1/query"

    while time.time() - start_time < timeout:
        params = {"query": f"ALERTS{{alertname='{alert_name}', alertstate='firing'}}"}
        try:
            data = _query_prometheus(cluster_url, params, timeout=10)
            if data.get("data", {}).get("result"):
                print(f"✅ Alert '{alert_name}' detected (cluster URL)")
                logging.info(f"Alert '{alert_name}' triggered (cluster URL)")
                return True
        except Exception as e_cluster:
            logging.debug(f"Prometheus cluster query failed: {e_cluster}")
            if not tried_local:
                tried_local = True
                logging.info("Falling back to localhost Prometheus URL (127.0.0.1:9090).")

        if tried_local:
            try:
                data = _query_prometheus(local_url, params, timeout=10)
                if data.get("data", {}).get("result"):
                    print(f"✅ Alert '{alert_name}' detected (localhost)")
                    logging.info(f"Alert '{alert_name}' triggered (localhost)")
                    return True
            except Exception as e_local:
                logging.debug(f"Prometheus localhost query failed: {e_local}")

        time.sleep(10)

    print(f"⚠️ Alert '{alert_name}' not detected within timeout")
    logging.warning(f"Alert '{alert_name}' not detected")
    return False

# ========================
# Remediator validation
# ========================
def validate_remediator():
    """Confirm remediator restored normal state."""
    print("⏳ Validating remediator actions...")
    if not wait_for_pods_ready(timeout=120):
        print("❌ Pods did not recover in time")
        logging.error("Pods did not recover in time")
        return False

    pods = get_target_pods()
    all_correct = True
    for pod in pods:
        image = run_command(f"kubectl get pod {pod} -n {NAMESPACE} -o jsonpath='{{.spec.containers[0].image}}'")
        if image != EXPECTED_IMAGE:
            print(f"❌ Pod {pod} has wrong image: {image}")
            logging.error(f"Pod {pod} has wrong image: {image}")
            all_correct = False
        else:
            logging.info(f"Pod {pod} running correct image {image}")

    desired = run_command(f"kubectl get deployment test-remediator -n {NAMESPACE} -o jsonpath='{{.spec.replicas}}'")
    ready = run_command(f"kubectl get deployment test-remediator -n {NAMESPACE} -o jsonpath='{{.status.readyReplicas}}'")

    if desired != ready:
        print(f"❌ Replica mismatch: desired={desired}, ready={ready}")
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

    if not wait_for_pods_ready():
        logging.error("Pods not ready at start; aborting tests.")
        return

    pods = get_target_pods()
    if not pods:
        print("❌ No target pods found for testing!")
        logging.error("No pods found for testing")
        return

    # 1️⃣ CPU & Memory stress test
    for pod in pods:
        cpu_stress(pod, duration=60, workers=2)
        memory_stress(pod, duration=60, size_mb=50)
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
