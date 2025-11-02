#!/bin/bash

# -----------------------------
# ⚙️ Prometheus Rules Reload Script
# -----------------------------
# This script recreates the Prometheus rules ConfigMap
# and triggers a configuration reload without restarting pods.
# Run it anytime you modify alert_rules.yml.
# -----------------------------

NAMESPACE="monitoring"
RULES_FILE="module_3/k8s/prometheus/alert_rules.yml"
CONFIGMAP_NAME="prometheus-rules"

echo "🔍 Checking for rules file at $RULES_FILE..."
if [ ! -f "$RULES_FILE" ]; then
    echo "❌ Rules file not found! Please ensure $RULES_FILE exists."
    exit 1
fi

echo "🧹 Cleaning old ConfigMap (if any)..."
kubectl delete configmap $CONFIGMAP_NAME -n $NAMESPACE --ignore-not-found

echo "📦 Creating new ConfigMap from alert_rules.yml..."
kubectl create configmap $CONFIGMAP_NAME --from-file=$RULES_FILE -n $NAMESPACE

echo "🔍 Finding Prometheus pod..."
PROM_POD=$(kubectl get pod -n $NAMESPACE -l app=prometheus -o jsonpath="{.items[0].metadata.name}")

if [ -z "$PROM_POD" ]; then
    echo "❌ Prometheus pod not found! Check deployment status with:"
    echo "   kubectl get pods -n $NAMESPACE"
    exit 1
fi

echo "♻️ Triggering Prometheus config reload..."
kubectl exec -n $NAMESPACE $PROM_POD -- wget --quiet --method=POST http://localhost:9090/-/reload || {
    echo "⚠️ Reload failed — you may need to restart Prometheus manually."
    exit 1
}

echo "✅ Rules updated and Prometheus reloaded successfully."
