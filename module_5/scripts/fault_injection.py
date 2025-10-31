#!/usr/bin/env python3
# ============================================
# module_5/scripts/fault_injection.py  ✅ FINAL STABLE + SAFE EXIT + ROTATION + LOGFILE
# ============================================

import os
import subprocess
import time
import shutil
import sys
import threading
import signal
from http.server import BaseHTTPRequestHandler, HTTPServer
import socket
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

# ----------------------------------------------------
# ⚙️ Configuration (read selectable selector from env)
# ----------------------------------------------------
NAMESPACE = os.getenv("NAMESPACE", "monitoring")
LABEL_SELECTOR = os.getenv("LABEL_SELECTOR", "app=sample-app")  # default -> sample-app (Module 2)
METRICS_PORT = int(os.getenv("METRICS_PORT", "9090"))
RECHECK_INTERVAL = int(os.getenv("RECHECK_INTERVAL", "300"))  # seconds (5 minutes)
METRIC_RETENTION_LIMIT = int(os.getenv("METRIC_RETENTION_LIMIT", "50"))
LOG_FILE = Path(os.getenv("LOG_FILE", "/tmp/faultinjector.log"))
LOG_SIZE_LIMIT = int(os.getenv("LOG_SIZE_LIMIT", str(1 * 1024 * 1024)))  # 1 MB
LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "3"))

# ----------------------------------------------------
# 🪵 Logging Setup
# ----------------------------------------------------
logger = logging.getLogger("faultinjector")
logger.setLevel(logging.INFO)

handler = RotatingFileHandler(LOG_FILE, maxBytes=LOG_SIZE_LIMIT, backupCount=LOG_BACKUP_COUNT)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
handler.setFormatter(formatter)
logger.addHandler(handler)

console = logging.StreamHandler(sys.stdout)
console.setFormatter(formatter)
logger.addHandler(console)

logger.info("🧠 Fault Injector initialized with logfile rotation.")

# ----------------------------------------------------
# 📊 Health & Metrics State
# ----------------------------------------------------
health_status = {
    "alive": 1,
    "start_time": time.time(),
    "injections": 0,
    "kill_count": 0,
    "last_injection_time": 0,
    "pod_metrics": {},
}

shutdown_flag = False  # global flag for clean exit

# ----------------------------------------------------
# 🩺 Prometheus /metrics endpoint
# ----------------------------------------------------
class MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/metrics":
            try:
                uptime = int(time.time() - health_status["start_time"])
                last_injection = (
                    int(time.time() - health_status["last_injection_time"])
                    if health_status["last_injection_time"]
                    else -1
                )

                metrics = f"""# HELP faultinjector_health Fault injector health (1=alive)
# TYPE faultinjector_health gauge
faultinjector_health{{namespace="{NAMESPACE}"}} {health_status['alive']}

# HELP faultinjector_uptime_seconds Injector uptime in seconds
# TYPE faultinjector_uptime_seconds counter
faultinjector_uptime_seconds{{namespace="{NAMESPACE}"}} {uptime}

# HELP faultinjector_total_injections Total number of injections
# TYPE faultinjector_total_injections counter
faultinjector_total_injections{{namespace="{NAMESPACE}"}} {health_status['injections']}

# HELP faultinjector_kill_count Total pods killed
# TYPE faultinjector_kill_count counter
faultinjector_kill_count{{namespace="{NAMESPACE}"}} {health_status['kill_count']}

# HELP faultinjector_last_injection_age_seconds Seconds since last injection (-1 if none)
# TYPE faultinjector_last_injection_age_seconds gauge
faultinjector_last_injection_age_seconds{{namespace="{NAMESPACE}"}} {last_injection}
"""

                metrics += "\n# HELP faultinjector_pod_kills Faults injected per pod\n"
                metrics += "# TYPE faultinjector_pod_kills counter\n"
                for pod, pdata in health_status["pod_metrics"].items():
                    metrics += (
                        f'faultinjector_pod_kills{{namespace="{NAMESPACE}",pod="{pod}"}} {pdata.get("kill",0)}\n'
                    )

                self.send_response(200)
                self.send_header("Content-type", "text/plain; version=0.0.4")
                self.end_headers()
                self.wfile.write(metrics.encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f"# error: {e}\n".encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        return  # suppress default HTTP logs


def start_metrics_server():
    """Persistent /metrics endpoint with auto-restart."""
    while not shutdown_flag:
        try:
            socket.setdefaulttimeout(5)
            server = HTTPServer(("0.0.0.0", METRICS_PORT), MetricsHandler)
            logger.info(f"✅ Metrics endpoint running on port {METRICS_PORT} (/metrics)")
            server.serve_forever()
        except Exception as e:
            if shutdown_flag:
                break
            logger.warning(f"⚠️ Metrics server crashed: {e}. Restarting in 5s...")
            time.sleep(5)


# ----------------------------------------------------
# 🧹 Log Rotation & Cleanup
# ----------------------------------------------------
def rotate_metrics():
    """Trim pod metrics dictionary to prevent memory bloat."""
    while not shutdown_flag:
        if len(health_status["pod_metrics"]) > METRIC_RETENTION_LIMIT:
            excess = len(health_status["pod_metrics"]) - METRIC_RETENTION_LIMIT
            for i, key in enumerate(list(health_status["pod_metrics"].keys())):
                if i < excess:
                    del health_status["pod_metrics"][key]
            logger.info(f"🧹 Rotated metrics: kept last {METRIC_RETENTION_LIMIT} pods")
        time.sleep(600)


# ----------------------------------------------------
# 🧪 Fault Injection Logic
# ----------------------------------------------------
def check_kubectl():
    if not shutil.which("kubectl"):
        logger.error("❌ 'kubectl' not found in PATH.")
        sys.exit(1)

def run_command(cmd, capture_stderr=True):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    out = result.stdout.strip()
    if result.returncode != 0:
        err = result.stderr.strip()
        if err:
            logger.debug(f"Command stderr: {err}")
        logger.warning(f"⚠️ Command failed: {cmd} (rc={result.returncode})")
    return out

def record_pod_metric(pod):
    if pod not in health_status["pod_metrics"]:
        health_status["pod_metrics"][pod] = {"kill": 0}
    health_status["pod_metrics"][pod]["kill"] += 1

def get_pods():
    # LABEL_SELECTOR might be like 'app=sample-app'
    output = run_command(f"kubectl get pods -l {LABEL_SELECTOR} -n {NAMESPACE} -o name || true")
    pods = [p.replace("pod/", "") for p in output.splitlines() if p.strip()]
    if not pods:
        logger.warning(f"⚠️ No pods found with selector '{LABEL_SELECTOR}' in namespace '{NAMESPACE}'.")
    return pods

def is_self_pod(pod_name: str) -> bool:
    """Return True if pod is likely the injector itself (never target self)."""
    low = pod_name.lower()
    if "faultinjector" in low or "test-remediator" in low:
        return True
    # also skip pods that match the injector's service account label if any
    return False

def kill_pod(pod_name):
    logger.info(f"💥 Killing pod {pod_name}...")
    run_command(f"kubectl delete pod {pod_name} -n {NAMESPACE} --wait=false || true")
    health_status["kill_count"] += 1
    record_pod_metric(pod_name)
    logger.info(f"✅ Pod {pod_name} deletion requested.")

def inject_faults():
    check_kubectl()
    pods = get_pods()
    if not pods:
        return

    for pod in pods:
        if shutdown_flag:
            return
        # never target ourselves
        if is_self_pod(pod):
            logger.warning(f"⛔ Skipping self-targeting pod: {pod}")
            continue

        status = run_command(f"kubectl get pod {pod} -n {NAMESPACE} -o jsonpath='{{.status.phase}}' || true")
        if not status or status.lower() != "running":
            logger.warning(f"⚠️ Pod {pod} not running ({status}). Skipping.")
            continue

        try:
            kill_pod(pod)
            health_status["injections"] += 1
            health_status["last_injection_time"] = time.time()
            # small wait to allow kube to schedule alerts/rollouts
            time.sleep(5)
        except Exception as e:
            logger.error(f"⚠️ Error killing {pod}: {e}")


def run_continuous_loop():
    while not shutdown_flag:
        logger.info("🔁 Starting new fault injection cycle...")
        try:
            inject_faults()
        except Exception as e:
            logger.error(f"⚠️ Fault injection error: {e}")
        if shutdown_flag:
            break
        logger.info(f"⏸️ Sleeping for {RECHECK_INTERVAL}s before next cycle...")
        time.sleep(RECHECK_INTERVAL)


# ----------------------------------------------------
# 🧨 Graceful Exit Handler
# ----------------------------------------------------
def graceful_exit(signum, frame):
    global shutdown_flag
    shutdown_flag = True
    logger.info("🛑 Received termination signal. Cleaning up safely...")
    health_status["alive"] = 0
    uptime = int(time.time() - health_status["start_time"])
    logger.info(f"🧾 Summary: {health_status['injections']} injections | {health_status['kill_count']} kills | Uptime: {uptime}s")
    sys.exit(0)


# ----------------------------------------------------
# 🚀 Main Entrypoint
# ----------------------------------------------------
if __name__ == "__main__":
    signal.signal(signal.SIGINT, graceful_exit)
    signal.signal(signal.SIGTERM, graceful_exit)

    # log current config
    logger.info(f"Config: NAMESPACE={NAMESPACE}, LABEL_SELECTOR={LABEL_SELECTOR}, METRICS_PORT={METRICS_PORT}")

    threading.Thread(target=start_metrics_server, daemon=True).start()
    threading.Thread(target=rotate_metrics, daemon=True).start()

    logger.info("🚀 Module 5 Fault Injector started. Press Ctrl+C to exit safely.\n")
    run_continuous_loop()
