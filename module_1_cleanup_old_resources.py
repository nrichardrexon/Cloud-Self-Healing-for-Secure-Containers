# module_1_cleanup_old_resources.py
import subprocess
import sys

DEPLOYMENTS = ["checkpoint1-app", "sample-app-deployment"]
SERVICES = ["checkpoint1-service", "sample-app-service"]
DOCKER_IMAGES = ["checkpoint1-app:latest", "sample-app:latest"]

def run_command(cmd, check=True):
    """Run a shell command and print output."""
    try:
        print(f"Running: {cmd}")
        result = subprocess.run(cmd, shell=True, check=check,
                                text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running command:\n{e.output}")
        if check:
            sys.exit(1)
        return False

def delete_k8s_resources():
    """Delete deployments and services if they exist."""
    for deploy in DEPLOYMENTS:
        run_command(f"kubectl delete deployment {deploy} --ignore-not-found")
    for svc in SERVICES:
        run_command(f"kubectl delete service {svc} --ignore-not-found")

def delete_docker_images():
    """Delete old Docker images."""
    for image in DOCKER_IMAGES:
        run_command(f"docker rmi {image} --force || true")

def main():
    print("⚠ Starting cleanup of old Kubernetes resources and Docker images...")
    delete_k8s_resources()
    delete_docker_images()
    print("\n✅ Cleanup complete!")

if __name__ == "__main__":
    main()
