# ============================================
# module_5/scripts/fault_injection.py  ✅ FINAL FIXED
# ============================================

import subprocess
import time
import shutil
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import socket

NAMESPACE = "monitoring"
LABEL_SELECTOR = "app=faultinjector"
METRICS_PORT = 9090
RECHECK_INTERVAL = 300  # Run fault injection every 5 min

# ----------------------------------------------------
# 🩺 Simple /metrics endpoint for Prometheus
# ----------------------------------------------------
health_status = {"alive": 1, "start_time": time.time(), "injections": 0}


class MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/metrics":
            try:
                uptime = int(time.time() - health_status["start_time"])
                metrics = (
                    "# HELP faultinjector_health Module 5 fault injector health (1=alive)\n"
                    "# TYPE faultinjector_health gauge\n"
                    f"faultinjector_health {health_status['alive']}\n"
                    "# HELP faultinjector_uptime_seconds Module 5 uptime in seconds\n"
                    "# TYPE faultinjector_uptime_seconds counter\n"
                    f"faultinjector_uptime_seconds {uptime}\n"
                    "# HELP faultinjector_total_injections Total number of fault injections performed\n"
                    "# TYPE faultinjector_total_injections counter\n"
                    f"faultinjector_total_injections {health_status['injections']}\n"
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
        # Silence default HTTP logs
        return


def start_metrics_server():
    """Persistent /metrics endpoint with retry on crash."""
    while True:
        try:
            socket.setdefaulttimeout(5)
            server = HTTPServer(("0.0.0.0", METRICS_PORT), MetricsHandler)
            print(f"✅ Metrics endpoint running on port {METRICS_PORT} (/metrics)")
            server.serve_forever()
        except Exception as e:
            print(f"⚠️ Metrics server crashed: {e}. Restarting in 5s...")
            time.sleep(5)


def heartbeat_updater():
    """Continuously updates Prometheus-visible health signals."""
    while True:
        health_status["alive"] = 1
        time.sleep(15)


# ----------------------------------------------------
# 🧪 Fault injection logic
# ----------------------------------------------------
def check_kubectl():
    if not shutil.which("kubectl"):
        print("❌ Error: 'kubectl' not found in container. Install it or rebuild the image.")
        sys.exit(1)


def run_command(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"⚠️ Command failed: {cmd}\n{result.stderr.strip()}")
    return result.stdout.strip()


def kill_pod(pod_name):
    print(f"💥 Killing pod {pod_name}...")
    run_command(f"kubectl delete pod {pod_name} -n {NAMESPACE}")


def stress_cpu(pod_name, duration=30):
    print(f"🔥 Stressing CPU in pod {pod_name} for {duration}s...")
    run_command(f"kubectl exec {pod_name} -n {NAMESPACE} -- sh -c 'yes > /dev/null &'")
    time.sleep(duration)
    run_command(f"kubectl exec {pod_name} -n {NAMESPACE} -- pkill yes")
    print("✅ CPU stress completed.")


def stress_memory(pod_name, duration=30, size_mb=100):
    print(f"💾 Stressing memory in pod {pod_name} ({size_mb}MB) for {duration}s...")
    run_command(
        f"kubectl exec {pod_name} -n {NAMESPACE} -- sh -c "
        f"'python3 -c \"a = [\'x\'*1024*1024]*{size_mb}; import time; time.sleep({duration})\" &'"
    )
    time.sleep(duration)
    run_command(f"kubectl exec {pod_name} -n {NAMESPACE} -- pkill -f 'python3 -c'")
    print("✅ Memory stress completed.")


def get_pods():
    output = run_command(f"kubectl get pods -l {LABEL_SELECTOR} -n {NAMESPACE} -o name")
    pods = [p.replace("pod/", "") for p in output.splitlines()]
    if not pods:
        print("⚠️ No pods found with the given label.")
    return pods


def inject_faults():
    check_kubectl()
    pods = get_pods()
    if not pods:
        return

    for pod in pods:
        status = run_command(f"kubectl get pod {pod} -n {NAMESPACE} -o jsonpath='{{.status.phase}}'")
        if status.lower() != "running":
            print(f"⚠️ Pod {pod} is not running ({status}). Skipping fault injection.")
            continue

        kill_pod(pod)
        time.sleep(5)
        stress_cpu(pod)
        stress_memory(pod)
        health_status["injections"] += 1


def run_continuous_loop():
    """Repeats fault injection periodically without blocking metrics endpoint."""
    while True:
        print("🔁 Starting new fault injection cycle...")
        try:
            inject_faults()
        except Exception as e:
            print(f"⚠️ Fault injection error: {e}")
        print(f"⏸️ Sleeping for {RECHECK_INTERVAL}s before next cycle...")
        time.sleep(RECHECK_INTERVAL)


# ----------------------------------------------------
# 🚀 Main entrypoint
# ----------------------------------------------------
if __name__ == "__main__":
    threading.Thread(target=start_metrics_server, daemon=True).start()
    threading.Thread(target=heartbeat_updater, daemon=True).start()

    # Continuous operation
    run_continuous_loop()
