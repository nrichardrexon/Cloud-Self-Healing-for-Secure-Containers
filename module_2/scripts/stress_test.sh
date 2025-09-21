#!/bin/bash
# Simple CPU & Memory stress test for Module 2 pods

CPU_LOAD=${1:-1}       # Number of CPU cores to stress (default: 1)
DURATION=${2:-30}      # Duration in seconds (default: 30s)

POD_LABEL="app=module-2-sample-app"

echo "Fetching pods for stress test..."
PODS=$(kubectl get pods -l $POD_LABEL -o jsonpath='{.items[*].metadata.name}')

for POD in $PODS; do
  echo "Running stress test on pod: $POD"
  kubectl exec $POD -- bash -c "apt-get update && apt-get install -y stress && stress --cpu $CPU_LOAD --timeout $DURATION"
done

echo "Stress test completed!"
