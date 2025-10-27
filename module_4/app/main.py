# ============================================================
# Module 4 — Remediator & Actions (Final Version – Stable & Monitored)
# ============================================================

from fastapi import FastAPI, Request
import yaml
import os
import logging
import subprocess
import time
from threading import Lock

# ---------------------------------------------------------
# Optional Prometheus instrumentation
# ---------------------------------------------------------
try:
    from prometheus_fastapi_instrumentator import Instrumentator
    PROM_AVAILABLE = True
except ImportError:
    PROM_AVAILABLE = False

# ---------------------------------------------------------
# App setup
# ---------------------------------------------------------
app = FastAPI(title="Module 4 Remediator", version="1.0.2")

# ---------------------------------------------------------
# Logging setup (safe for non-root container)
# ---------------------------------------------------------
LOG_DIR = os.getenv("LOG_DIR", "/tmp/logs")  # /tmp is always writable
os.makedirs(LOG_DIR, exist_ok=True)
LOG_PATH = os.path.join(LOG_DIR, "remediator.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("remediator")

logger.info(f"📂 Logging initialized at {LOG_PATH}")

# ---------------------------------------------------------
# Load remediation policies
# ---------------------------------------------------------
POLICIES_FILE = os.getenv("POLICIES_FILE", "/app/policies.yaml")
if not os.path.exists(POLICIES_FILE):
    raise FileNotFoundError(f"Missing policies file: {POLICIES_FILE}")

with open(POLICIES_FILE, "r") as f:
    POLICIES = yaml.safe_load(f) or {}

logger.info(f"✅ Loaded {len(POLICIES)} remediation policies")

# ---------------------------------------------------------
# Safety state (cooldowns, overrides)
# ---------------------------------------------------------
cooldown_seconds = int(os.getenv("COOLDOWN_SECONDS", "60"))
last_executed = {}
manual_override = False
lock = Lock()

# ---------------------------------------------------------
# Health and override endpoints
# ---------------------------------------------------------
@app.get("/health")
async def health():
    """Health and safety state check."""
    return {
        "status": "healthy",
        "manual_override": manual_override,
        "policy_count": len(POLICIES),
        "metrics_enabled": PROM_AVAILABLE
    }

@app.post("/override/on")
async def enable_override():
    """Pause auto-remediation."""
    global manual_override
    manual_override = True
    logger.warning("🛑 Manual override ENABLED – auto-remediation paused")
    return {"manual_override": manual_override}

@app.post("/override/off")
async def disable_override():
    """Resume auto-remediation."""
    global manual_override
    manual_override = False
    logger.info("✅ Manual override DISABLED – auto-remediation active")
    return {"manual_override": manual_override}

# ---------------------------------------------------------
# Alerts endpoint
# ---------------------------------------------------------
@app.post("/alerts")
async def receive_alerts(request: Request):
    """Receive alert payloads from Alertmanager and trigger actions."""
    data = await request.json()
    logger.info(f"📨 Received alert payload: {data}")

    if manual_override:
        logger.warning("⚠ Manual override active – ignoring alerts")
        return {"status": "ignored", "reason": "manual_override"}

    for alert in data.get("alerts", []):
        alertname = alert.get("labels", {}).get("alertname", "")
        action = POLICIES.get(alertname)
        if action:
            execute_action_with_safety(action, alertname)
        else:
            logger.warning(f"No action defined for alert '{alertname}'")

    return {"status": "processed"}

# ---------------------------------------------------------
# Safety wrapper for cooldown
# ---------------------------------------------------------
def execute_action_with_safety(action: str, alertname: str):
    """Avoid repeated execution of same action within cooldown period."""
    with lock:
        now = time.time()
        last_time = last_executed.get(action, 0)
        if now - last_time < cooldown_seconds:
            logger.info(f"⏳ Cooldown active for '{action}' – skipped execution")
            return
        last_executed[action] = now
    execute_action(action, alertname)

# ---------------------------------------------------------
# Execute actual kubectl or remediation action
# ---------------------------------------------------------
def execute_action(action: str, alertname: str):
    """Run remediation command safely."""
    try:
        logger.info(f"🚀 Executing '{action}' for alert '{alertname}'")
        result = subprocess.run(
            action.split(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        logger.info(f"✅ Action '{action}' completed:\n{result.stdout}")
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Failed to execute '{action}': {e.stderr or e}")
    except Exception as ex:
        logger.exception(f"⚠ Unexpected error while executing '{action}': {ex}")

# ---------------------------------------------------------
# Optional endpoint for dry-run testing
# ---------------------------------------------------------
@app.post("/simulate")
async def simulate_action(action: str):
    """Simulate a remediation action without executing."""
    logger.info(f"🧪 Simulated action: {action}")
    return {"simulated": action}

# ---------------------------------------------------------
# Prometheus metrics exposure
# ---------------------------------------------------------
if os.getenv("ENABLE_METRICS", "true").lower() == "true" and PROM_AVAILABLE:
    try:
        Instrumentator().instrument(app).expose(app)
        logger.info("📈 Prometheus metrics endpoint enabled at /metrics")
    except Exception as e:
        logger.error(f"⚠ Failed to expose metrics endpoint: {e}")
else:
    logger.info("⚙️ Metrics instrumentation disabled or library unavailable")

# ---------------------------------------------------------
# Run FastAPI (container entrypoint)
# ---------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
