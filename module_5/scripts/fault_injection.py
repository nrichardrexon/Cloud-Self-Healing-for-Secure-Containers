# module_5/scripts/fault_injection.py
import subprocess
import time
import shutil
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

NAMESPACE = "monitoring"
LABEL_SELECTOR = "app=faultinjector"
METRICS_PORT = 9090

# ----------------------------------------------------
# 🩺 Simple /metrics endpoint for Prometheus
# ----------------------------------------------------
health_status = {"alive": 1, "last_update": time.time()}

class MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/metrics":
            self.send_response(200)
            self.send_header("Content-type", "text/plain; version=0.0.4")
            self.end_headers()

            uptime = int(time.time() - health_status["last_update"])
            metrics = (
                f"faultinjector_health {health_status['alive']}\n"
                f"faultinjector_uptime_seconds {uptime}\n"
            )
            self.wfile.write(metrics.encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

def start_metrics_server():
    while True:
        try:
            server = HTTPServer(("0.0.0.0", METRICS_PORT), MetricsHandler)
            print(f"✅ Metrics endpoint running on port {METRICS_PORT} (/metrics)")
            server.serve_forever()
        except Exception as e:
            print(f"⚠️ Metrics server crashed: {e}. Restarting in 5s...")
            time.sleep(5)

def heartbeat_updater():
    """Continuously updates the metrics heartbeat so Prometheus sees the target as alive."""
    while True:
        health_status["alive"] = 1
        health_status["last_update"] = time.time()
        time.sleep(15)  # Update every 15 seconds

# ----------------------------------------------------
# 🧪 Fault injection logic (existing)
# ----------------------------------------------------
def check_kubectl():
    if not shutil.which("kubectl"):
        print("❌ Error: 'kubectl' not found in container. Install it or rebuild the image.")
        sys.exit(1)

def run_command(cmd):
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"⚠️ Command failed: {result.stderr.strip()}")
    return result.stdout.strip()

def kill_pod(pod_name):
    print(f"💥 Killing pod {pod_name}...")
    run_command(f"kubectl delete pod {pod_name} -n {NAMESPACE}")

def stress_cpu(pod_name, duration=30):
    print(f"🔥 Stressing CPU in pod {pod_name} for {duration}s...")
    run_command(
        f"kubectl exec {pod_name} -n {NAMESPACE} -- sh -c 'yes > /dev/null &'"
    )
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
    output = run_command(
        f"kubectl get pods -l {LABEL_SELECTOR} -n {NAMESPACE} -o name"
    )
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
        status = run_command(
            f"kubectl get pod {pod} -n {NAMESPACE} -o jsonpath='{{.status.phase}}'"
        )
        if status.lower() != "running":
            print(f"⚠️ Pod {pod} is not running ({status}). Skipping fault injection.")
            continue

        kill_pod(pod)
        time.sleep(5)
        stress_cpu(pod)
        stress_memory(pod)

# ----------------------------------------------------
# 🚀 Main entrypoint
# ----------------------------------------------------
if __name__ == "__main__":
    # Start /metrics endpoint in background
    threading.Thread(target=start_metrics_server, daemon=True).start()

    # Start health heartbeat updater
    threading.Thread(target=heartbeat_updater, daemon=True).start()

    # Run fault injector loop
    inject_faults()
