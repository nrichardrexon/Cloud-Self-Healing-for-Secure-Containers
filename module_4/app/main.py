from fastapi import FastAPI, Request
import yaml
import os
import logging
import subprocess

app = FastAPI(title="Module 4 Remediator")

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

# Load policies from ConfigMap-mounted file
POLICIES_FILE = "/app/policies.yaml"
with open(POLICIES_FILE) as f:
    POLICIES = yaml.safe_load(f)

@app.post("/alerts")
async def receive_alerts(request: Request):
    data = await request.json()
    logging.info(f"Received alert: {data}")

    for alert in data.get("alerts", []):
        alertname = alert.get("labels", {}).get("alertname", "")
        action = POLICIES.get(alertname)
        if action:
            logging.info(f"Executing action '{action}' for alert '{alertname}'")
            execute_action(action, alert)
        else:
            logging.warning(f"No action defined for alert '{alertname}'")
    return {"status": "ok"}

def execute_action(action: str, alert: dict):
    """
    Executes remediation actions: restart, rollback, scale, quarantine
    """
    try:
        if action.startswith("restart:"):
            pod_name = action.split(":")[1]
            subprocess.run(["kubectl", "delete", "pod", pod_name], check=True)
            logging.info(f"Restarted pod {pod_name}")

        elif action.startswith("rollback:"):
            deploy = action.split(":")[1]
            subprocess.run(["kubectl", "rollout", "undo", f"deployment/{deploy}"], check=True)
            logging.info(f"Rolled back deployment {deploy}")

        elif action.startswith("scale:"):
            deploy, replicas = action.split(":")[1].split(",")
            subprocess.run(["kubectl", "scale", f"deployment/{deploy}", f"--replicas={replicas}"], check=True)
            logging.info(f"Scaled deployment {deploy} to {replicas} replicas")

        elif action.startswith("quarantine:"):
            pod_name = action.split(":")[1]
            subprocess.run(["kubectl", "label", "pod", pod_name, "quarantine=true", "--overwrite"], check=True)
            logging.info(f"Quarantined pod {pod_name}")

    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to execute action {action}: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
