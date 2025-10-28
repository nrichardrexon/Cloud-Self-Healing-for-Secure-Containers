# ============================================
# module_5/scripts/fault_injection.py  ✅ FINAL (Per-Pod + Namespace Metrics)
# ============================================

import subprocess
import time
import shutil
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import socket

# ----------------------------------------------------
# ⚙️ Configuration
# ----------------------------------------------------
NAMESPACE = "monitoring"
LABEL_SELECTOR = "app=faultinjector"
METRICS_PORT = 9090
RECHECK_INTERVAL = 300  # seconds (5 minutes)

# ----------------------------------------------------
# 📊 Health & Metrics State
# ----------------------------------------------------
health_status = {
    "alive": 1,
    "start_time": time.time(),
    "injections": 0,
    "kill_count": 0,
    "cpu_stress_count": 0,
    "memory_stress_count": 0,
    "last_injection_time": 0,
    "pod_metrics": {},  # per-pod metrics storage
}


# ----------------------------------------------------
# 🩺 Prometheus /metrics endpoint
# ----------------------------------------------------
class MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/metrics":
            try:
                uptime = int(time.time() - health_status["start_time"])
                last_injection = int(
                    time.time() - health_status["last_injection_time"]
                ) if health_status["last_injection_time"] else -1

                # Base global metrics
                metrics = f"""# HELP faultinjector_health Module 5 fault injector health (1=alive)
# TYPE faultinjector_health gauge
faultinjector_health{{namespace="{NAMESPACE}"}} {health_status['alive']}

# HELP faultinjector_uptime_seconds Injector uptime
# TYPE faultinjector_uptime_seconds counter
faultinjector_uptime_seconds{{namespace="{NAMESPACE}"}} {uptime}

# HELP faultinjector_total_injections Total number of fault injections performed
# TYPE faultinjector_total_injections counter
faultinjector_total_injections{{namespace="{NAMESPACE}"}} {health_status['injections']}

# HELP faultinjector_last_injection_age_seconds Seconds since last injection (-1 if none)
# TYPE faultinjector_last_injection_age_seconds gauge
faultinjector_last_injection_age_seconds{{namespace="{NAMESPACE}"}} {last_injection}
"""

                # Per-pod labeled metrics
                metrics += "\n# HELP faultinjector_pod_faults Total faults injected per pod\n"
                metrics += "# TYPE faultinjector_pod_faults counter\n"

                for pod, pdata in health_status["pod_metrics"].items():
                    metrics += (
                        f'faultinjector_pod_faults{{namespace="{NAMESPACE}",pod="{pod}",type="kill"}} {pdata.get("kill",0)}\n'
                        f'faultinjector_pod_faults{{namespace="{NAMESPACE}",pod="{pod}",type="cpu_stress"}} {pdata.get("cpu",0)}\n'
                        f'faultinjector_pod_faults{{namespace="{NAMESPACE}",pod="{pod}",type="memory_stress"}} {pdata.get("memory",0)}\n'
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
        return  # silence default HTTP logs


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
# 🧪 Fault Injection Logic
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


def record_pod_metric(pod, fault_type):
    if pod not in health_status["pod_metrics"]:
        health_status["pod_metrics"][pod] = {"kill": 0, "cpu": 0, "memory": 0}
    health_status["pod_metrics"][pod][fault_type] += 1


def kill_pod(pod_name):
    print(f"💥 Killing pod {pod_name}...")
    run_command(f"kubectl delete pod {pod_name} -n {NAMESPACE}")
    health_status["kill_count"] += 1
    record_pod_metric(pod_name, "kill")


def stress_cpu(pod_name, duration=30):
    print(f"🔥 Stressing CPU in pod {pod_name} for {duration}s...")
    run_command(f"kubectl exec {pod_name} -n {NAMESPACE} -- sh -c 'yes > /dev/null &'")
    time.sleep(duration)
    run_command(f"kubectl exec {pod_name} -n {NAMESPACE} -- pkill yes")
    health_status["cpu_stress_count"] += 1
    record_pod_metric(pod_name, "cpu")
    print("✅ CPU stress completed.")


def stress_memory(pod_name, duration=30, size_mb=100):
    print(f"💾 Stressing memory in pod {pod_name} ({size_mb}MB) for {duration}s...")
    run_command(
        f"kubectl exec {pod_name} -n {NAMESPACE} -- sh -c "
        f"'python3 -c \"a = [\\'x\\'*1024*1024]*{size_mb}; import time; time.sleep({duration})\" &'"
    )
    time.sleep(duration)
    run_command(f"kubectl exec {pod_name} -n {NAMESPACE} -- pkill -f 'python3 -c'")
    health_status["memory_stress_count"] += 1
    record_pod_metric(pod_name, "memory")
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
        health_status["last_injection_time"] = time.time()


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
# 🚀 Main Entrypoint
# ----------------------------------------------------
if __name__ == "__main__":
    threading.Thread(target=start_metrics_server, daemon=True).start()
    threading.Thread(target=heartbeat_updater, daemon=True).start()
    run_continuous_loop()
