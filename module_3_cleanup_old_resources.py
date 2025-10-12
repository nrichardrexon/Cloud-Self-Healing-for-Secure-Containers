# module_3_cleanup_full.py
import subprocess

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

def run_command(cmd):
    print(f"Running: {cmd}")
    subprocess.run(cmd, shell=True, check=False)

def cleanup():
    print("⚠ Starting full cleanup of Module 3 resources...")

    # Delete Deployments
    run_command(f"kubectl delete deployment {PROM_DEPLOYMENT} --namespace {NAMESPACE} --ignore-not-found")
    run_command(f"kubectl delete deployment {ALERT_DEPLOYMENT} --namespace {NAMESPACE} --ignore-not-found")

    # Delete Services
    run_command(f"kubectl delete service {PROM_SERVICE} --namespace {NAMESPACE} --ignore-not-found")
    run_command(f"kubectl delete service {ALERT_SERVICE} --namespace {NAMESPACE} --ignore-not-found")

    # Delete ConfigMaps
    run_command(f"kubectl delete configmap {PROM_CONFIGMAP} --namespace {NAMESPACE} --ignore-not-found")
    run_command(f"kubectl delete configmap {ALERT_CONFIGMAP} --namespace {NAMESPACE} --ignore-not-found")

    # Delete Secrets
    run_command(f"kubectl delete secret {ALERT_SECRET} --namespace {NAMESPACE} --ignore-not-found")

    # Optional: Delete the entire namespace (uncomment to reset everything)
    # run_command(f"kubectl delete namespace {NAMESPACE} --ignore-not-found")

    # Remove Docker images
    run_command(f"docker rmi {PROM_DOCKER_IMAGE} --force || true")
    run_command(f"docker rmi {ALERT_DOCKER_IMAGE} --force || true")

    print("✅ Full Module 3 cleanup complete!")

if __name__ == "__main__":
    cleanup()
