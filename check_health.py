# check_health.py
import subprocess

def run(cmd, label=None):
    """Run a shell command and return status, output."""
    try:
        result = subprocess.run(cmd, shell=True, check=True, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        status = "✅"
        output = result.stdout.strip()
    except subprocess.CalledProcessError as e:
        status = "❌"
        output = e.output.strip()
    if label:
        print(f"\n{label}: {status}\n{output}")
    else:
        print(f"\n{cmd}: {status}\n{output}")

def main():
    print("=== Project Health Check ===")

    # Python
    run("python --version", "Python Version")
    run("which python", "Python Path")
    run("ls -l app/smain.py", "App File Check")

    # Docker
    run("docker --version", "Docker Version")
    run("docker images", "Docker Images")
    run("docker ps -a", "Docker Containers")

    # Kind & Kubernetes
    run("kind --version", "Kind Version")
    run("kubectl cluster-info", "Kubernetes Cluster Info")
    run("kubectl get nodes", "Kubernetes Nodes")
    run("kubectl get pods -A", "All Pods")

    # Git
    run("git status", "Git Status")
    run("git log --oneline -5", "Last 5 Git Commits")

    # Kubernetes Deployments & Services
    run("kubectl get deployments", "K8s Deployments")
    run("kubectl get services", "K8s Services")
    run("kubectl describe pods --show-events", "Pod Details & Events")

    print("\n=== Health Check Complete ===")

if __name__ == "__main__":
    main()
