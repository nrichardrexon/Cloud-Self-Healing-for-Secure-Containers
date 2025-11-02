#!/usr/bin/env python3
# ========================================= 
# ✅ module_5_functional_test.py (Dynamic Pod Discovery – Final)
# Purpose: Validate self-healing by injecting controlled faults and verifying alerts
# Notes:
# - Dynamically discovers pods by prefix.
# - Attempts to run stress inside target pod; if 'stress' missing, creates stress-tester pod and runs stress there.
# - More robust error handling and clearer logging.
# =========================================

import subprocess
import time
from pathlib import Path
import logging
import requests
import os
import sys

# ========================
# Configuration
# ========================
NAMESPACE = "monitoring"
PROMETHEUS_URL = os.getenv(
    "PROMETHEUS_URL",
    "http://prometheus.monitoring.svc.cluster.local:9090/api/v1/query"
)
LOG_FILE = Path(__file__).parent / "functional_test.log"

# *** Updated to match the image we load into kind/local cluster ***
EXPECTED_IMAGE = "module5-faultinjector:latest"
FAULTY_IMAGE = "busybox:nonexistent"
PROMETHEUS_TIMEOUT = 90
TARGET_CONTAINER = "faultinjector"

STRESS_TESTER_NAME = "stress-tester"   # ephemeral pod used when stress binary missing
STRESS_TESTER_IMAGE = "progrium/stress"  # small image with stress tool
STRESS_TIMEOUT = 60  # seconds for stress runs when called from script

# track whether we created the stress-tester so we only remove what we created
_stress_tester_created = False

# ========================
# Logging setup
# ========================
logging.basicConfig(
    filename=LOG_FILE,
    filemode="a",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Also print to stdout for interactive debugging
console = logging.StreamHandler(sys.stdout)
console.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
console.setFormatter(formatter)
logging.getLogger().addHandler(console)


# ========================
# Helpers
# ========================
def run_command(cmd: str, check: bool = False, timeout: int = 120) -> str:
    """Run a shell command and return stdout/stderr combined (trimmed). Longer default timeout."""
    logging.info(f"Running: {cmd}")
    try:
        result = subprocess.run(
            cmd, shell=True, check=check, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout
        )
        out = result.stdout.strip()
        if out:
            logging.info(out)
        return out
    except subprocess.CalledProcessError as e:
        logging.error(f"Command failed ({cmd}):\n{e.output}")
        return e.output.strip() if e.output else ""
    except subprocess.TimeoutExpired as e:
        logging.error(f"Command timed out ({cmd}): {e}")
        return ""


def kubectl_jsonpath_names(namespace: str = NAMESPACE) -> list:
    """Return list of pod names in namespace using jsonpath for reliability."""
    cmd = f"kubectl get pods -n {namespace} -o jsonpath='{{.items[*].metadata.name}}'"
    out = run_command(cmd, timeout=20)
    return [p for p in out.split() if p]


def get_dynamic_pod(prefix: str, namespace: str = NAMESPACE):
    """
    Find a running pod whose name includes prefix.
    Prefer Running-phase pods.
    """
    try:
        pods = kubectl_jsonpath_names(namespace)
        matching = [p for p in pods if prefix in p]
        if not matching:
            logging.warning(f"No pods found for prefix '{prefix}' in namespace '{namespace}'")
            return None

        # prefer Running pods
        for pod in matching:
            phase = run_command(f"kubectl get pod {pod} -n {namespace} -o jsonpath='{{.status.phase}}'", timeout=10)
            if phase == "Running":
                logging.info(f"Found running pod for prefix '{prefix}': {pod}")
                return pod

        # otherwise return first match
        logging.info(f"Found pod for prefix '{prefix}' (not Running): {matching[0]}")
        return matching[0]
    except Exception as e:
        logging.error(f"Error in get_dynamic_pod: {e}")
        return None


def wait_for_pods_ready(prefixes=("remediator", "faultinjector"), timeout=120):
    """Wait for at least one Running pod matching each prefix (timeout seconds)."""
    logging.info("⏳ Waiting for pods to be ready (dynamic check)...")
    start = time.time()
    while time.time() - start < timeout:
        ok = True
        for prefix in prefixes:
            pod = get_dynamic_pod(prefix)
            if not pod:
                ok = False
                break
            phase = run_command(f"kubectl get pod {pod} -n {NAMESPACE} -o jsonpath='{{.status.phase}}'", timeout=10)
            if phase != "Running":
                ok = False
                break
        if ok:
            logging.info("✅ Required pods are Running")
            return True
        time.sleep(3)
    logging.warning("⚠️ Timeout waiting for pods to become ready.")
    return False


# ========================
# Stress-tester management (fallback)
# ========================
def stress_tester_exists() -> bool:
    out = run_command(f"kubectl get pod -n {NAMESPACE} {STRESS_TESTER_NAME} -o jsonpath='{{.status.phase}}' || true", timeout=10)
    return bool(out and "Error from server" not in out)


def create_stress_tester():
    """Create a small pod that has stress available and runs as root so it can stress other pods."""
    global _stress_tester_created
    logging.info(f"Creating stress-tester pod '{STRESS_TESTER_NAME}' in {NAMESPACE} (if missing)")
    yaml = f"""
apiVersion: v1
kind: Pod
metadata:
  name: {STRESS_TESTER_NAME}
  namespace: {NAMESPACE}
  labels:
    app: {STRESS_TESTER_NAME}
spec:
  containers:
    - name: stress
      image: {STRESS_TESTER_IMAGE}
      command: ["sleep", "3600"]
      securityContext:
        runAsUser: 0
  restartPolicy: Never
"""
    run_command(f"kubectl apply -f - <<'YAML'\n{yaml}\nYAML", timeout=30)
    _stress_tester_created = True


def wait_for_stress_tester_ready(timeout=60):
    start = time.time()
    while time.time() - start < timeout:
        phase = run_command(f"kubectl get pod -n {NAMESPACE} {STRESS_TESTER_NAME} -o jsonpath='{{.status.phase}}' || true", timeout=10)
        if phase == "Running":
            logging.info("Stress-tester pod is Running")
            return True
        logging.info("Waiting for stress-tester to be Running...")
        time.sleep(2)
    logging.error("Stress-tester did not become Running in time")
    return False


def remove_stress_tester():
    global _stress_tester_created
    if not _stress_tester_created:
        logging.info("Stress-tester was not created by this script; skipping removal.")
        return
    logging.info("Cleaning up stress-tester pod (if exists)")
    run_command(f"kubectl delete pod -n {NAMESPACE} {STRESS_TESTER_NAME} --ignore-not-found", timeout=20)
    _stress_tester_created = False


def pod_has_stress(pod: str) -> bool:
    """Check whether stress binary exists in given pod."""
    out = run_command(f"kubectl exec -n {NAMESPACE} {pod} -- which stress || true", timeout=10)
    return bool(out and "which: no" not in out and "not found" not in out)


def exec_via_stress_tester(args: str, timeout: int = 120) -> str:
    """Run stress using the stress-tester pod (create if needed)."""
    if not stress_tester_exists():
        create_stress_tester()
        if not wait_for_stress_tester_ready(timeout=60):
            raise RuntimeError("stress-tester pod failed to start")

    cmd = f"kubectl exec -n {NAMESPACE} {STRESS_TESTER_NAME} -- /bin/sh -c \"{args}\""
    return run_command(cmd, timeout=timeout)


# ========================
# Fault injection functions
# ========================
def _exec_with_retries(cmd, retries=3, delay=2, timeout=120):
    """Exec shell cmd with small retry loop. Return output or last error text."""
    last = ""
    for attempt in range(1, retries + 1):
        last = run_command(cmd, timeout=timeout)
        if last and "not found" not in last and "Error from server" not in last and "command terminated with exit code 127" not in last:
            return last
        logging.debug(f"Attempt {attempt} failed or command not present; retrying in {delay}s")
        time.sleep(delay)
    return last


def cpu_stress(pod, duration=60, workers=2):
    """Inject CPU stress — try inside target pod, else use stress-tester pod."""
    logging.info(f"⚡ Injecting CPU stress into {pod} for {duration}s")
    cmd = f"kubectl exec -n {NAMESPACE} {pod} -- /bin/sh -c \"stress --cpu {workers} --timeout {duration}\""
    out = _exec_with_retries(cmd, timeout=duration + 30)
    if out and "command terminated with exit code 127" not in out and "not found" not in out:
        logging.info(f"CPU stress executed inside {pod}")
        return out

    # fallback: use stress-tester (container has stress)
    logging.info("stress missing in target pod — falling back to stress-tester pod")
    try:
        return exec_via_stress_tester(f"stress --cpu {workers} --timeout {duration}", timeout=duration + 60)
    except Exception as e:
        logging.error(f"Failed to run stress via stress-tester: {e}")
        return ""


def memory_stress(pod, duration=60, size_mb=100):
    """Inject memory stress — try inside target pod, else use stress-tester pod."""
    logging.info(f"⚡ Injecting memory stress into {pod} for {duration}s ({size_mb}MB)")
    cmd = f"kubectl exec -n {NAMESPACE} {pod} -- /bin/sh -c \"stress --vm 1 --vm-bytes {size_mb}M --timeout {duration}\""
    out = _exec_with_retries(cmd, timeout=duration + 30)
    if out and "command terminated with exit code 127" not in out and "not found" not in out:
        logging.info(f"Memory stress executed inside {pod}")
        return out

    logging.info("stress missing in target pod — falling back to stress-tester pod")
    try:
        return exec_via_stress_tester(f"stress --vm 1 --vm-bytes {size_mb}M --timeout {duration}", timeout=duration + 60)
    except Exception as e:
        logging.error(f"Failed to run memory stress via stress-tester: {e}")
        return ""


def kill_main_process(pod):
    """Kill main Python process in target pod."""
    logging.info(f"⚡ Killing main process inside {pod}")
    pid = run_command(f"kubectl exec -n {NAMESPACE} {pod} -- pgrep -o python3 || true", timeout=10)
    if pid and pid.strip().isdigit():
        run_command(f"kubectl exec -n {NAMESPACE} {pod} -- kill -9 {pid.strip()}", timeout=10)
        logging.info(f"Killed PID {pid.strip()} in {pod}")
    else:
        logging.warning(f"No python process found in {pod}")


def deploy_faulty_image():
    """Deploy broken image to test faultinjector recovery (now uses faultinjector deployment)."""
    logging.info("⚡ Deploying faulty image to faultinjector")
    run_command(f"kubectl set image deployment/faultinjector {TARGET_CONTAINER}={FAULTY_IMAGE} -n {NAMESPACE}", timeout=30)


# ========================
# Prometheus alert verification
# ========================
def _query_prometheus(url, params, timeout=10):
    resp = requests.get(url, params=params, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def check_prometheus_alert(alert_name, timeout=PROMETHEUS_TIMEOUT):
    """Check if Prometheus alert fired."""
    logging.info(f"⏳ Checking for alert: {alert_name}")
    start = time.time()
    tried_local = False
    cluster_url = PROMETHEUS_URL
    local_url = "http://127.0.0.1:9090/api/v1/query"

    while time.time() - start < timeout:
        params = {"query": f"ALERTS{{alertname='{alert_name}', alertstate='firing'}}"}
        try:
            data = _query_prometheus(cluster_url, params)
            if data.get("data", {}).get("result"):
                logging.info(f"✅ Alert '{alert_name}' detected (cluster)")
                return True
        except Exception as e:
            logging.debug(f"Prometheus cluster query failed: {e}")
            if not tried_local:
                tried_local = True
                logging.info("Falling back to localhost Prometheus (port-forward if needed)")

        if tried_local:
            try:
                data = _query_prometheus(local_url, params)
                if data.get("data", {}).get("result"):
                    logging.info(f"✅ Alert '{alert_name}' detected (localhost)")
                    return True
            except Exception as e:
                logging.debug(f"Local Prometheus query failed: {e}")

        time.sleep(5)

    logging.warning(f"⚠️ Alert '{alert_name}' not detected within timeout")
    return False


# ========================
# Remediator validation
# ========================
def validate_remediator():
    logging.info("⏳ Validating remediator recovery...")
    if not wait_for_pods_ready(timeout=120):
        logging.error("Pods did not recover in time")
        return False

    # *** check faultinjector pod/image now (was test-remediator previously) ***
    pod = get_dynamic_pod("faultinjector")
    if not pod:
        logging.error("No running faultinjector pod found")
        return False

    image = run_command(f"kubectl get pod {pod} -n {NAMESPACE} -o jsonpath='{{.spec.containers[0].image}}'", timeout=10)
    if image != EXPECTED_IMAGE:
        logging.error(f"Wrong image detected for {pod}: {image}")
        return False

    desired = run_command(f"kubectl get deployment faultinjector -n {NAMESPACE} -o jsonpath='{{.spec.replicas}}'", timeout=10)
    ready = run_command(f"kubectl get deployment faultinjector -n {NAMESPACE} -o jsonpath='{{.status.readyReplicas}}'", timeout=10)
    if desired != ready:
        logging.error(f"Replica mismatch: desired={desired} ready={ready}")
        return False

    logging.info("✅ Remediator validated successfully")
    return True


# ========================
# Functional testing workflow
# ========================
def run_functional_tests():
    logging.info("=== 🚀 Starting Dynamic Functional Tests ===")

    if not wait_for_pods_ready():
        logging.error("Initial pods not ready — aborting tests")
        return

    # dynamically discover pods (now preferring faultinjector)
    test_pod = get_dynamic_pod("faultinjector")
    cadvisor_pod = get_dynamic_pod("cadvisor")
    kubelet_pod = get_dynamic_pod("kubelet")
    faultinjector_pod = get_dynamic_pod("faultinjector")

    if not any([test_pod, cadvisor_pod, kubelet_pod, faultinjector_pod]):
        logging.error("No target pods found for testing")
        return

    # 1️⃣ Stress & alert tests (on faultinjector when available)
    if test_pod:
        cpu_stress(test_pod, duration=STRESS_TIMEOUT, workers=2)
        memory_stress(test_pod, duration=STRESS_TIMEOUT, size_mb=50)
        check_prometheus_alert("HighCPUUsage")
        check_prometheus_alert("HighMemoryUsage")
        validate_remediator()

    # 2️⃣ Process kill simulation
    if test_pod:
        kill_main_process(test_pod)
        check_prometheus_alert("ContainerCrash")
        validate_remediator()

    # 3️⃣ Faulty image test (now targets faultinjector deployment)
    deploy_faulty_image()
    check_prometheus_alert("DeploymentFailed")
    validate_remediator()

    # 4️⃣ Optionally report monitoring pod status
    for label, pod in {"cadvisor": cadvisor_pod, "kubelet": kubelet_pod, "faultinjector": faultinjector_pod}.items():
        if pod:
            phase = run_command(f"kubectl get pod {pod} -n {NAMESPACE} -o jsonpath='{{.status.phase}}'", timeout=10)
            logging.info(f"ℹ️ {label} pod {pod} status: {phase}")

    # cleanup stress-tester if created (leave if you want to reuse)
    remove_stress_tester()

    logging.info("✅ Functional testing complete!")


# ========================
# Entry point
# ========================
if __name__ == "__main__":
    run_functional_tests()
