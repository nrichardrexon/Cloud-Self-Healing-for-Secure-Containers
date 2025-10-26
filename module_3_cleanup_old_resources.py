# module_3_cleanup_full.py
import subprocess
import os
import signal

# Module 3 resources
NAMESPACE = "monitoring"
PROM_DEPLOYMENT = "prometheus"
ALERT_DEPLOYMENT = "alertmanager"
PROM_SERVICE = "prometheus"
ALERT_SERVICE = "alertmanager"
PROM_CONFIGMAP = "prometheus-config"
ALERT_CONFIGMAP = "alertmanager-config"
ALERT_SECRET = "alertmanager-credentials"

PROM_DOCKER_IMAGE = "prom/prometheus:v2.52.0"
ALERT_DOCKER_IMAGE = "prom/alertmanager:v0.27.0"

PORT_FORWARD_PORTS = [9090, 9093]  # ports to check for lingering port-forward processes

def run_command(cmd):
    print(f"Running: {cmd}")
    subprocess.run(cmd, shell=True, check=False)

def kill_port_forward_processes(ports):
    """Terminate any kubectl port-forward processes on the specified ports."""
    for port in ports:
        try:
            # Find processes using the port
            result = subprocess.run(
                f"lsof -ti tcp:{port}",
                shell=True, capture_output=True, text=True
            )
            pids = result.stdout.strip().split()
            for pid in pids:
                if pid:
                    print(f"🛑 Terminating port-forward process PID {pid} on port {port}")
                    os.kill(int(pid), signal.SIGTERM)
        except Exception as e:
            print(f"⚠ Could not terminate port {port}: {e}")

def cleanup():
    print("⚠ Starting full cleanup of Module 3 resources...")

    # Kill lingering port-forward processes
    kill_port_forward_processes(PORT_FORWARD_PORTS)

    # Delete Deployments
    run_command(f"kubectl delete deployment {PROM_DEPLOYMENT} -n {NAMESPACE} --ignore-not-found")
    run_command(f"kubectl delete deployment {ALERT_DEPLOYMENT} -n {NAMESPACE} --ignore-not-found")

    # Delete Services
    run_command(f"kubectl delete service {PROM_SERVICE} -n {NAMESPACE} --ignore-not-found")
    run_command(f"kubectl delete service {ALERT_SERVICE} -n {NAMESPACE} --ignore-not-found")

    # Delete ConfigMaps
    run_command(f"kubectl delete configmap {PROM_CONFIGMAP} -n {NAMESPACE} --ignore-not-found")
    run_command(f"kubectl delete configmap {ALERT_CONFIGMAP} -n {NAMESPACE} --ignore-not-found")

    # Delete Secrets
    run_command(f"kubectl delete secret {ALERT_SECRET} -n {NAMESPACE} --ignore-not-found")

    # Optional: Delete the namespace entirely
    # run_command(f"kubectl delete namespace {NAMESPACE} --ignore-not-found")

    # Remove Docker images if pulled locally
    run_command(f"docker rmi {PROM_DOCKER_IMAGE} --force || true")
    run_command(f"docker rmi {ALERT_DOCKER_IMAGE} --force || true")

    print("✅ Full Module 3 cleanup complete!")

if __name__ == "__main__":
    cleanup()
