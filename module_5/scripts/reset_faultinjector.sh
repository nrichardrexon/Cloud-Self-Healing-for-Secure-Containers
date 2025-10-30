#!/bin/bash
# ===============================================
# 🧹 Fault Injector Reset Script (Module 5)
# ===============================================
# Purpose: Clean up all existing faultinjector pods,
# replicasets, and deployments in the monitoring namespace,
# then redeploy the correct definition.
# ===============================================

set -e  # Exit immediately on error
NAMESPACE="monitoring"
LABEL="app=faultinjector"
DEPLOY_FILE="/workspaces/Cloud-Self-Healing-for-Secure-Containers/module_5/k8s/faultinjector-deployment.yaml"

echo "🚀 Starting faultinjector reset in namespace: ${NAMESPACE}"
echo "---------------------------------------------"

# 1️⃣ Delete old Deployments, ReplicaSets, and Pods
echo "🧹 Cleaning old deployments, replicasets, and pods..."
kubectl delete deploy -n "$NAMESPACE" -l "$LABEL" --ignore-not-found
kubectl delete rs -n "$NAMESPACE" -l "$LABEL" --ignore-not-found
kubectl delete pod -n "$NAMESPACE" -l "$LABEL" --ignore-not-found

# 2️⃣ Wait for cleanup to complete
echo "⏳ Waiting for resource cleanup..."
sleep 5

# 3️⃣ Redeploy the latest correct definition
echo "📦 Reapplying deployment from: ${DEPLOY_FILE}"
kubectl apply -f "$DEPLOY_FILE"

# 4️⃣ Wait for pod to come up
echo "🔍 Watching for new pod readiness..."
kubectl wait --for=condition=ready pod -l "$LABEL" -n "$NAMESPACE" --timeout=60s || true

# 5️⃣ Display pod status
echo "---------------------------------------------"
kubectl get pods -n "$NAMESPACE" -l "$LABEL" -o wide
echo "✅ Faultinjector reset complete!"
