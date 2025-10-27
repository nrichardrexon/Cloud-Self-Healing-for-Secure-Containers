# ============================================================
# Module 4 — Remediator & Actions (Final Version)
# ============================================================

from fastapi import FastAPI, Request
import yaml
import os
import logging
import subprocess
import time
from threading import Lock

app = FastAPI(title="Module 4 Remediator")

# ---------------------------------------------------------
# Setup logging (console + file)
# ---------------------------------------------------------
os.makedirs("/app/logs", exist_ok=True)
LOG_PATH = "/app/logs/remediator.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler()
    ]
)

# ---------------------------------------------------------
# Load remediation policies
# ---------------------------------------------------------
POLICIES_FILE = "/app/policies.yaml"
if not os.path.exists(POLICIES_FILE):
    raise FileNotFoundError(f"Missing policies file: {POLICIES_FILE}")

with open(POLICIES_FILE, "r") as f:
    POLICIES = yaml.safe_load(f)

# ---------------------------------------------------------
# Safety state (cooldowns, overrides)
# ---------------------------------------------------------
cooldown_seconds = 60        # prevent same action within 60 seconds
last_executed = {}           # {action: timestamp}
manual_override = False      # disable automation when True
lock = Lock()

# ---------------------------------------------------------
# Health and override endpoints
# ---------------------------------------------------------
@app.get("/health")
async def health():
    """Health and safety state check."""
    return {"status": "healthy", "manual_override": manual_override}

@app.post("/override/on")
async def enable_override():
    """Pause auto-remediation."""
    global manual_override
    manual_override = True
    logging.warning("🛑 Manual override ENABLED – auto-remediation paused")
    return {"manual_override": manual_override}

@app.post("/override/off")
async def disable_override():
    """Resume auto-remediation."""
    global manual_override
    manual_override = False
    logging.info("✅ Manual override DISABLED – auto-remediation active")
    return {"manual_override": manual_override}

# ---------------------------------------------------------
# Alerts endpoint
# ---------------------------------------------------------
@app.post("/alerts")
async def receive_alerts(request: Request):
    """Receive alert payloads from Alertmanager and trigger actions."""
    data = await request.json()
    logging.info(f"📨 Received alert payload: {data}")

    if manual_override:
        logging.warning("⚠ Manual override active – ignoring alerts")
        return {"status": "ignored", "reason": "manual_override"}

    for alert in data.get("alerts", []):
        alertname = alert.get("labels", {}).get("alertname", "")
        action = POLICIES.get(alertname)
        if action:
            execute_action_with_safety(action, alertname)
        else:
            logging.warning(f"No action defined for alert '{alertname}'")

    return {"status": "processed"}

# ---------------------------------------------------------
# Safety wrapper for cooldown
# ---------------------------------------------------------
def execute_action_with_safety(action: str, alertname: str):
    with lock:
        now = time.time()
        last_time = last_executed.get(action, 0)
        if now - last_time < cooldown_seconds:
            logging.info(f"⏳ Cooldown active for '{action}' – skipped execution")
            return
        last_executed[action] = now
    execute_action(action, alertname)

# ---------------------------------------------------------
# Execute actual kubectl or remediation action
# ---------------------------------------------------------
def execute_action(action: str, alertname: str):
    try:
        logging.info(f"🚀 Executing '{action}' for alert '{alertname}'")
        subprocess.run(action.split(), check=True)
        logging.info(f"✅ Action '{action}' completed successfully")
    except subprocess.CalledProcessError as e:
        logging.error(f"❌ Failed to execute '{action}': {e}")

# ---------------------------------------------------------
# Optional endpoint for dry-run testing
# ---------------------------------------------------------
@app.post("/simulate")
async def simulate_action(action: str):
    """Simulate a remediation action without executing."""
    logging.info(f"🧪 Simulated action: {action}")
    return {"simulated": action}

# ---------------------------------------------------------
# Run FastAPI (container entrypoint)
# ---------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
