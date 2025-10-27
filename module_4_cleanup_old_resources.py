# module_4_cleanup_old_resources.py
import subprocess

# Module 4 resources
NAMESPACE = "monitoring"
REM_DEPLOYMENT = "remediator"
REM_SERVICE = "remediator"
REM_CONFIGMAP = "remediator-policies"
LOCAL_IMAGE = "remediator:latest"

def run_command(cmd, check=False):
    """Run a shell command and print output."""
    print(f"Running: {cmd}")
    subprocess.run(cmd, shell=True, check=check, text=True)

def cleanup():
    print("⚠ Starting cleanup of Module 4 resources...")

    # Delete Deployment
    run_command(f"kubectl delete deployment {REM_DEPLOYMENT} --namespace {NAMESPACE} --ignore-not-found")

    # Delete Service
    run_command(f"kubectl delete service {REM_SERVICE} --namespace {NAMESPACE} --ignore-not-found")

    # Delete ConfigMap
    run_command(f"kubectl delete configmap {REM_CONFIGMAP} --namespace {NAMESPACE} --ignore-not-found")

    # Remove local Kind image
    print(f"🧹 Removing local Kind image '{LOCAL_IMAGE}'")
    run_command(f"kind load docker-image {LOCAL_IMAGE} --name kind --nodes kind-control-plane --delete")

    print("✅ Module 4 cleanup complete!")

if __name__ == "__main__":
    cleanup()
