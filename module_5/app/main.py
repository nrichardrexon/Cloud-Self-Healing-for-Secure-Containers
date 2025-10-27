import yaml
import random
import subprocess
import time
import os

POLICY_FILE = "policies.yaml"

def run_cmd(cmd):
    """Run shell commands safely."""
    try:
        print(f"▶ {cmd}")
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Command failed: {e.stderr}")

def load_policies():
    with open(POLICY_FILE, "r") as f:
        docs = yaml.safe_load(f)
    data = docs.get("data", {}).get("policies", "")
    return yaml.safe_load(data)

def apply_fault(policy):
    print(f"🧪 Applying fault: {policy['name']} — {policy['description']}")
    namespace = policy["namespace"]
    label = policy["targetLabel"]

    if "pod_kill" in policy["name"]:
        cmd = f"kubectl delete pod -n {namespace} -l {label} --grace-period=0 --force"
    else:
        cmd = f"kubectl get pods -n {namespace} -l {label}"
    run_cmd(cmd)

def main():
    policies = load_policies()
    print(f"✅ Loaded {len(policies)} fault policies.")

    while True:
        policy = random.choice(policies)
        apply_fault(policy)
        wait_time = random.randint(20, 60)
        print(f"⏳ Waiting {wait_time}s before next fault...")
        time.sleep(wait_time)

if __name__ == "__main__":
    main()
