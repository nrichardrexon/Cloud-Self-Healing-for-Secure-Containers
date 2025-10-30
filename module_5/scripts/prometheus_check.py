#!/usr/bin/env python3
"""
Prometheus Alert Checker
Queries the Prometheus server for a specific alert name and returns its state.
"""

import requests
import sys
import time

PROMETHEUS_URL = "http://prometheus.monitoring.svc.cluster.local:9090/api/v1/alerts"

def check_alert(alert_name, timeout=60, interval=5):
    """Wait for a specific Prometheus alert to become active."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = requests.get(PROMETHEUS_URL, timeout=5)
            if resp.status_code == 200:
                alerts = resp.json().get("data", {}).get("alerts", [])
                for alert in alerts:
                    if alert_name in alert.get("labels", {}).get("alertname", "") and alert["state"] == "firing":
                        print(f"✅ Alert '{alert_name}' detected!")
                        return True
            time.sleep(interval)
        except Exception as e:
            print(f"⚠️ Error querying Prometheus: {e}")
            time.sleep(interval)
    print(f"❌ Alert '{alert_name}' not detected within timeout.")
    return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python prometheus_check.py <AlertName>")
        sys.exit(1)
    alert_name = sys.argv[1]
    success = check_alert(alert_name)
    sys.exit(0 if success else 1)
