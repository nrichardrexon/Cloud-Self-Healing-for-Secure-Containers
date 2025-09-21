import subprocess

commands = [
    "helm repo add prometheus-community https://prometheus-community.github.io/helm-charts",
    "helm repo update",
    "helm install prometheus prometheus-community/kube-prometheus-stack -n monitoring --create-namespace",
    "kubectl apply -f monitoring/prometheus.yaml -n monitoring",
    "kubectl apply -f monitoring/alertmanager.yaml -n monitoring",
    "kubectl apply -f monitoring/alert_rules.yaml -n monitoring",
    "docker run -d   -p 9090:9090   -v /workspaces/Cloud-Self-Healing-for-Secure-Containers/monitoring/prometheus.yaml:/etc/prometheus/prometheus.yml   -v /workspaces/Cloud-Self-Healing-for-Secure-Containers/monitoring/alert_rules.yml:/etc/prometheus/alert_rules.yml   prom/prometheus:v2.52.0",
    "kubectl get pods -n monitoring"
]

for cmd in commands:
    print(f"Running: {cmd}")
    subprocess.run(cmd, shell=True, check=True)