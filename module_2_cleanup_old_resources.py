# module_2_cleanup_old_resources.py
import subprocess

DEPLOYMENT_NAME = "module-2-sample-app"
SERVICE_NAME = "module-2-sample-app-service"
DOCKER_IMAGE = "module-2-sample-app:latest"

def run_command(cmd):
    print(f"Running: {cmd}")
    subprocess.run(cmd, shell=True, check=False)

def cleanup():
    print("⚠ Starting cleanup of old Kubernetes resources and Docker images...")
    run_command(f"kubectl delete deployment {DEPLOYMENT_NAME} --ignore-not-found")
    run_command(f"kubectl delete service {SERVICE_NAME} --ignore-not-found")
    run_command(f"docker rmi {DOCKER_IMAGE} --force || true")
    print("✅ Cleanup complete!")

if __name__ == "__main__":
    cleanup()
