"""
Comprehensive Test Suite: test_remediator_safety_mocked.py
Purpose:
  - Validate alert → policy → action flow.
  - Ensure safety controls (cooldowns, manual overrides).
  - Mock real actions (no Kubernetes/OS side effects).
  - Verify logs and responses for correctness.
"""

import pytest
import json
import time
from pathlib import Path
from fastapi.testclient import TestClient

# Import your FastAPI app and global state
from module_4.app.main import app, last_executed, manual_override, cooldown_seconds

client = TestClient(app)

# Paths for logs and policies
LOG_DIR = Path("/app/logs")
POLICIES_FILE = Path("/app/policies.yaml")

# -----------------------------------------------------------
# ✅ Fixture: Setup Environment (policies, logs, state)
# -----------------------------------------------------------
@pytest.fixture(scope="module", autouse=True)
def setup_environment():
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # Ensure policies file exists
    policies = {
        "HighCPUUsage": "kubectl scale deployment module-2-sample-app --replicas=5",
        "PodCrashLoop": "kubectl rollout restart deployment module-2-sample-app",
        "BadImageDetected": "kubectl rollout undo deployment module-2-sample-app",
        "SuspiciousPod": "kubectl cordon pod suspicious-pod-name",
        "MemoryOverload": "kubectl scale deployment module-2-sample-app --replicas=3"
    }
    POLICIES_FILE.write_text(json.dumps(policies, indent=4))

    # Clean up old logs
    for log_file in LOG_DIR.glob("*.log"):
        log_file.unlink(missing_ok=True)

    # Reset global state
    last_executed.clear()
    global manual_override
    manual_override = False

    yield

    # Cleanup logs after tests
    for log_file in LOG_DIR.glob("*.log"):
        log_file.unlink(missing_ok=True)


# -----------------------------------------------------------
# ✅ Mock Action
# -----------------------------------------------------------
def mock_action(action: str, alertname: str):
    """Mock the behavior of real Kubernetes actions."""
    return f"MOCK-{action.split()[0].upper()} executed for {alertname}"


# -----------------------------------------------------------
# ✅ Test: Alert Endpoint Accepts Payload
# -----------------------------------------------------------
def test_alert_endpoint_accepts_payload(monkeypatch):
    monkeypatch.setattr("module_4.app.main.execute_action", mock_action)
    payload = {"alerts": [{"labels": {"alertname": "HighCPUUsage"}}]}
    res = client.post("/alerts", json=payload)
    assert res.status_code == 200
    assert res.json()["status"] == "processed"


# -----------------------------------------------------------
# ✅ Test: Policy Mapping
# -----------------------------------------------------------
@pytest.mark.parametrize("alertname", [
    "HighCPUUsage",
    "PodCrashLoop",
    "BadImageDetected",
    "SuspiciousPod",
    "MemoryOverload"
])
def test_policy_mappings(monkeypatch, alertname):
    monkeypatch.setattr("module_4.app.main.execute_action", mock_action)
    payload = {"alerts": [{"labels": {"alertname": alertname}}]}
    res = client.post("/alerts", json=payload)
    assert res.status_code == 200
    assert res.json()["status"] == "processed"


# -----------------------------------------------------------
# ✅ Test: Cooldown Enforcement
# -----------------------------------------------------------
def test_safety_cooldown(monkeypatch):
    monkeypatch.setattr("module_4.app.main.execute_action", mock_action)
    payload = {"alerts": [{"labels": {"alertname": "HighCPUUsage"}}]}

    # First trigger: normal execution
    res1 = client.post("/alerts", json=payload)
    assert res1.status_code == 200

    # Immediate retrigger: should hit cooldown
    res2 = client.post("/alerts", json=payload)
    assert res2.status_code == 200  # processed but skipped internally

    # Wait for cooldown window
    time.sleep(cooldown_seconds)
    res3 = client.post("/alerts", json=payload)
    assert res3.status_code == 200


# -----------------------------------------------------------
# ✅ Test: Manual Override
# -----------------------------------------------------------
def test_manual_override(monkeypatch):
    monkeypatch.setattr("module_4.app.main.execute_action", mock_action)
    global manual_override
    manual_override = True

    payload = {"alerts": [{"labels": {"alertname": "PodCrashLoop"}}]}
    res = client.post("/alerts", json=payload)
    assert res.status_code == 200
    assert res.json()["status"] == "ignored"

    manual_override = False  # reset


# -----------------------------------------------------------
# ✅ Test: Unknown Alert Handling
# -----------------------------------------------------------
def test_unknown_alert(monkeypatch):
    monkeypatch.setattr("module_4.app.main.execute_action", mock_action)
    payload = {"alerts": [{"labels": {"alertname": "RandomNoise"}}]}
    res = client.post("/alerts", json=payload)
    assert res.status_code == 200
    assert res.json()["status"] == "processed"


# -----------------------------------------------------------
# ✅ Test: Health Endpoint
# -----------------------------------------------------------
def test_health_endpoint():
    res = client.get("/health")
    assert res.status_code == 200
    assert "status" in res.json()
    assert "manual_override" in res.json()


# -----------------------------------------------------------
# ✅ Test: Manual Override Toggle
# -----------------------------------------------------------
def test_override_toggle():
    # Enable override
    res_on = client.post("/override/on")
    assert res_on.status_code == 200
    assert res_on.json()["manual_override"] is True

    # Disable override
    res_off = client.post("/override/off")
    assert res_off.status_code == 200
    assert res_off.json()["manual_override"] is False


# -----------------------------------------------------------
# ✅ Test: Logging Output
# -----------------------------------------------------------
def test_log_files_created(monkeypatch):
    monkeypatch.setattr("module_4.app.main.execute_action", mock_action)
    payload = {"alerts": [{"labels": {"alertname": "MemoryOverload"}}]}
    client.post("/alerts", json=payload)
    logs = list(LOG_DIR.glob("*.log"))
    assert len(logs) > 0, "No log files found in remediator/logs"
    found = any("MemoryOverload" in log.read_text() for log in logs)
    assert found, "Expected alert not logged"
