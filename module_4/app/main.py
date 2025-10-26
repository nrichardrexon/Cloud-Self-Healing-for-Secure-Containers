from fastapi import FastAPI, Request
import yaml
import os
import logging
import subprocess
import time
from datetime import datetime, timedelta

app = FastAPI(title="Module 4 Remediator")

# Setup logging
LOG_FILE = "/app/actions.log"
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

# Load policies from ConfigMap-mounted file
POLICIES_FILE = "/app/policies.yaml"
with open(POLICIES_FILE) as f:
    POLICIES = yaml.safe_load(f)

# Safety: cooldown dictionary to track last executed actions
ACTION_COOLDOWN = {}  # {alertname: datetime_of_last_action}
COOLDOWN_PERIOD = timedelta(seconds=60)  # 1-minute cooldown

# Optional: manual override
MANUAL_OVERRIDE_FILE = "/app/manual_override.flag"

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/alerts")
async def receive_alerts(request: Request):
    data = await request.json()
    logger.info(f"Received alert: {data}")

    executed_actions = []

    for alert in data.get("alerts", []):
        alertname = alert.get("labels", {}).get("alertname", "")
        action = POLICIES.get(alertname)

        # Check manual override
        if os.path.exists(MANUAL_OVERRIDE_FILE):
            logger.warning(f"Manual override present. Skipping action for alert '{alertname}'")
            continue

        # Check cooldown
        last_exec = ACTION_COOLDOWN.get(alertname)
        if last_exec and datetime.now() - last_exec < COOLDOWN_PERIOD:
            logger.info(f"Cooldown active. Skipping action for alert '{alertname}'")
            continue

        if action:
            logger.info(f"Executing action '{action}' for alert '{alertname}'")
            success = execute_action(action, alert)
            if success:
                executed_actions.append({"alert": alertname, "action": action})
                ACTION_COOLDOWN[alertname] = datetime.now()
        else:
            logger.warning(f"No action defined for alert '{alertname}'")

    return {"status": "ok", "executed": executed_actions}

def execute_action(action: str, alert: dict) -> bool:
    """
    Executes remediation actions: restart, rollback, scale, quarantine
    """
    try:
        if action.startswith("restart:"):
            pod_name = action.split(":")[1]
            subprocess.run(["kubectl", "delete", "pod", pod_name], check=True)
            logger.info(f"Restarted pod {pod_name}")

        elif action.startswith("rollback:"):
            deploy = action.split(":")[1]
            subprocess.run(["kubectl", "rollout", "undo", f"deployment/{deploy}"], check=True)
            logger.info(f"Rolled back deployment {deploy}")

        elif action.startswith("scale:"):
            deploy, replicas = action.split(":")[1].split(",")
            subprocess.run(["kubectl", "scale", f"deployment/{deploy}", f"--replicas={replicas}"], check=True)
            logger.info(f"Scaled deployment {deploy} to {replicas} replicas")

        elif action.startswith("quarantine:"):
            pod_name = action.split(":")[1]
            subprocess.run(["kubectl", "label", "pod", pod_name, "quarantine=true", "--overwrite"], check=True)
            logger.info(f"Quarantined pod {pod_name}")

        # Log executed action to file
        with open(LOG_FILE, "a") as f:
            f.write(f"{datetime.now()} - ALERT: {alert.get('labels', {}).get('alertname','')} - ACTION: {action}\n")

        return True

    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to execute action {action}: {e}")
        return False

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
