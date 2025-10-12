from fastapi import FastAPI
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

app = FastAPI(title="Module 2 Sample App")

# ----------------------------------------------------
# Prometheus Metric — Counts total incoming requests
# ----------------------------------------------------
REQUEST_COUNT = Counter(
    "app_requests_total",
    "Total number of requests served by the application"
)

# ----------------------------------------------------
# Root Endpoint
# ----------------------------------------------------
@app.get("/")
def read_root():
    REQUEST_COUNT.inc()
    return {"message": "Hello from Module 2 sample app!"}

# ----------------------------------------------------
# Health Check Endpoint (for probes)
# ----------------------------------------------------
@app.get("/health")
def health_check():
    return {"status": "healthy"}

# ----------------------------------------------------
# Metrics Endpoint (for Prometheus scraping)
# ----------------------------------------------------
@app.get("/metrics")
def metrics():
    """Expose Prometheus metrics"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

# ----------------------------------------------------
# Entrypoint (for container runtime)
# ----------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    # Host 0.0.0.0 ensures it’s accessible in container/pod.
    uvicorn.run(app, host="0.0.0.0", port=8000)
