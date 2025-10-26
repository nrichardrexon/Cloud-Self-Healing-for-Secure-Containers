from flask import Flask, request, jsonify
import subprocess
import json
import os
import time

app = Flask(__name__)

@app.route('/alert', methods=['POST'])
def handle_alert():
    alert_data = request.json
    if not alert_data or 'alerts' not in alert_data:
        return jsonify({"status": "error", "message": "Invalid alert format"}), 400
    
    for alert in alert_data['alerts']:
        labels = alert.get('labels', {})
        action = labels.get('action')
        namespace = labels.get('namespace')
        pod_name = labels.get('pod')
        deployment_name = labels.get('deployment')
        
        if action == 'restart':
            restart_pod(namespace, pod_name)
        elif action == 'scale':
            scale_deployment(namespace, deployment_name, 2)  # Scale to 2 replicas
        elif action == 'rollback':
            rollback_deployment(namespace, deployment_name)
        elif action == 'quarantine':
            quarantine_pod(namespace, pod_name)
    
    return jsonify({"status": "success"}), 200

def restart_pod(namespace, pod_name):
    """Delete a pod to let it restart"""
    try:
        subprocess.run(f"kubectl delete pod {pod_name} -n {namespace}", shell=True, check=True)
        print(f"Restarted pod {pod_name} in namespace {namespace}")
    except subprocess.CalledProcessError as e:
        print(f"Error restarting pod: {e}")

def scale_deployment(namespace, deployment_name, replicas):
    """Scale a deployment"""
    try:
        subprocess.run(f"kubectl scale deployment {deployment_name} --replicas={replicas} -n {namespace}", 
                      shell=True, check=True)
        print(f"Scaled deployment {deployment_name} to {replicas} replicas in namespace {namespace}")
    except subprocess.CalledProcessError as e:
        print(f"Error scaling deployment: {e}")

def rollback_deployment(namespace, deployment_name):
    """Rollback a deployment to previous revision"""
    try:
        subprocess.run(f"kubectl rollout undo deployment/{deployment_name} -n {namespace}", 
                      shell=True, check=True)
        print(f"Rolled back deployment {deployment_name} in namespace {namespace}")
    except subprocess.CalledProcessError as e:
        print(f"Error rolling back deployment: {e}")

def quarantine_pod(namespace, pod_name):
    """Create a NetworkPolicy to isolate the pod"""
    network_policy = f"""
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: quarantine-{pod_name}
  namespace: {namespace}
spec:
  podSelector:
    matchLabels:
      app: {pod_name}
  policyTypes:
  - Ingress
  - Egress
  ingress: []
  egress: []
"""
    try:
        with open("/tmp/quarantine-policy.yaml", "w") as f:
            f.write(network_policy)
        subprocess.run(f"kubectl apply -f /tmp/quarantine-policy.yaml", shell=True, check=True)
        print(f"Quarantined pod {pod_name} in namespace {namespace}")
    except subprocess.CalledProcessError as e:
        print(f"Error quarantining pod: {e}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)