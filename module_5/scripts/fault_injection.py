# module_5/scripts/fault_injection.py
import subprocess
import time
import shutil
import sys

NAMESPACE = "monitoring"
LABEL_SELECTOR = "app=faultinjector"

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
        # Skip pods that are not running
        status = run_command(
            f"kubectl get pod {pod} -n {NAMESPACE} -o jsonpath='{{.status.phase}}'"
        )
        if status.lower() != "running":
            print(f"⚠️ Pod {pod} is not running ({status}). Skipping fault injection.")
            continue

        # Kill pod
        kill_pod(pod)
        time.sleep(5)  # allow cluster to stabilize

        # Stress CPU
        stress_cpu(pod)

        # Stress Memory
        stress_memory(pod)

if __name__ == "__main__":
    inject_faults()
