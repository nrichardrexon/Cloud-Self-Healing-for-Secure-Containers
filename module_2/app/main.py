from fastapi import FastAPI
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

app = FastAPI(title="Module 2 Sample App")

# Prometheus metric: counts total requests
REQUEST_COUNT = Counter("app_requests_total", "Total number of requests to the app")

@app.get("/")
def read_root():
    REQUEST_COUNT.inc()
    return {"message": "Hello from Module 2 sample app!"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/metrics")
def metrics():
    """Expose Prometheus metrics"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

if __name__ == "__main__":
    import uvicorn
    # Use 0.0.0.0 so container/K8s pods are accessible, port 8000 matches deployment.yaml
    uvicorn.run(app, host="0.0.0.0", port=8000)
