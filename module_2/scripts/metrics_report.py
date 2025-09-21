import requests
import csv
import time
from prometheus_client.parser import text_string_to_metric_families

# Module 2 service endpoint
SERVICE_URL = "http://module-2-sample-app-service:8000/metrics"

# CSV report output
CSV_FILE = "module_2_metrics_report.csv"

# Number of samples and delay between each sample (seconds)
NUM_SAMPLES = 5
SAMPLE_INTERVAL = 2

def fetch_metrics():
    try:
        response = requests.get(SERVICE_URL, timeout=5)
        if response.status_code != 200:
            print(f"Failed to fetch metrics: {response.status_code}")
            return {}
        metrics = {}
        for family in text_string_to_metric_families(response.text):
            for sample in family.samples:
                metrics[sample.name] = sample.value
        return metrics
    except Exception as e:
        print(f"Error fetching metrics: {e}")
        return {}

def main():
    print("Collecting Module 2 metrics...")
    with open(CSV_FILE, mode="w", newline="") as csvfile:
        fieldnames = ["timestamp", "app_requests_total"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for i in range(NUM_SAMPLES):
            metrics = fetch_metrics()
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            row = {
                "timestamp": timestamp,
                "app_requests_total": metrics.get("app_requests_total", 0)
            }
            writer.writerow(row)
            print(f"[{timestamp}] Sample {i+1}/{NUM_SAMPLES} - Requests Total: {row['app_requests_total']}")
            time.sleep(SAMPLE_INTERVAL)

    print(f"Metrics collection complete. Report saved to {CSV_FILE}")

if __name__ == "__main__":
    main()
