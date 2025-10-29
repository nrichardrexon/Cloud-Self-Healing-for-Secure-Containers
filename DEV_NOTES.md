

🧭 DEVELOPER NOTES — CLOUD SELF-HEALING FOR SECURE CONTAINERS

Purpose:
This document records all one-time setup, deployment, and debugging actions performed during the development of the *Cloud Self-Healing for Secure Containers* project.
It acts as a master reference for rebuilding, testing, and maintaining the complete system across all five modules.

---

🧩 MODULE 1 – ENVIRONMENT & SETUP
Goal: Prepare local Kubernetes cluster, namespaces, and environment dependencies.

Summary:
• Created a local Kind cluster for isolated testing and validation.
• Verified node and namespace setup.
• Built and loaded the sample application image for cluster deployment.

Relevant one-time commands:
– kind create cluster with configuration file (kubernetes_kind_setup.yaml).
– Verify cluster nodes using kubectl get nodes.
– Apply and verify namespaces using kubectl apply -f module_1/k8s/namespace.yaml and kubectl get namespaces.
– Build the sample app image and load it into Kind using Docker build and kind load docker-image sample-app:latest.

---

🚀 MODULE 2 – APPLICATION & DEPLOYMENT
Goal: Deploy and expose the containerized sample application in the Kubernetes cluster.

Summary:
• Applied Deployment and Service manifests.
• Verified pods, deployments, and service exposure.
• Exposed service ports for local access and validated functionality.

Relevant one-time commands:
– Apply deployment and service YAML files for the sample app.
– Check pod and deployment status using kubectl get pods and kubectl get deployments.
– Expose app locally using port-forwarding on port 8080.
– View and monitor logs for application containers.

---

📊 MODULE 3 – MONITORING & ALERTS (PROMETHEUS + ALERTMANAGER)
Goal: Implement full observability stack for the cluster and app health monitoring.

Summary:
• Deployed Prometheus and Alertmanager to the monitoring namespace.
• Configured alert rules, service endpoints, and authentication.
• Resolved missing ServiceAccount issue preventing Prometheus pod creation.
• Validated targets and ensured successful rollout.

Relevant one-time commands:
– Apply all Prometheus and Alertmanager manifests including ConfigMaps, Deployments, Services, and Secrets.
– Verify setup with kubectl get pods -n monitoring and kubectl get svc -n monitoring.
– Debug deployment failures using kubectl describe replicaset and kubectl describe deployment prometheus.
– Apply missing Prometheus ServiceAccount file and restart deployment using kubectl rollout restart.
– Check logs for both Prometheus and Alertmanager to confirm running state.
– Port-forward Prometheus and Alertmanager to localhost ports 9090 and 9093 respectively.

---

🧠 MODULE 4 – REMEDIATOR & ACTIONS (FASTAPI)
Goal: Enable self-healing capabilities via a FastAPI-based remediation service.

Summary:
• Built and deployed the remediation container image.
• Integrated it with the Kubernetes monitoring setup for automated actions.
• Validated endpoints and health checks via FastAPI service.

Relevant one-time commands:
– Run remediator locally for validation using Python.
– Build and load remediator container image into Kind.
– Apply Kubernetes deployment and service YAMLs for remediator.
– Verify pod readiness, check health endpoint via port-forwarded URL on port 8000.

---

🧪 MODULE 5 – FAULT INJECTION & TESTING
Goal: Test the entire self-healing pipeline under stress and fault conditions.

Summary:
• Conducted fault injection tests to simulate container failures.
• Verified alert generation and auto-remediation triggers.
• Validated system recovery times and log events through Prometheus and Alertmanager.

Relevant one-time commands:
– Execute Python-based fault injection scripts.
– Monitor pod status and restarts using kubectl get pods and kubectl describe pod.
– Port-forward Prometheus to visualize live metrics and alert firing.
– Check active alerts and resolutions in Alertmanager logs.

---

⚙️ COMMON MAINTENANCE / DEBUGGING
Purpose: Provide standard recovery and reinitialization actions for system maintenance.

Relevant one-time commands:
– Delete all monitoring resources including ConfigMaps and Secrets.
– Verify namespaces and resources in monitoring namespace.
– Force-delete stuck pods when needed.
– Inspect deployment and configuration YAMLs to troubleshoot misconfigurations.
– Rollout restart of Prometheus and Alertmanager deployments after configuration changes.

---

🧾 LOCAL UTILITIES / CODESPACE TOOLS
Purpose: Validate Codespace setup and local cluster connectivity.

Relevant one-time commands:
– Install and use the tree command to visualize repository structure.
– List and verify current Kubernetes contexts.
– Check Prometheus readiness and targets through HTTP requests.

---

🧩 OPTIONAL – ML-AUGMENTED ALERT VALIDATION
Goal: Add intelligent anomaly validation to the alerting mechanism.

Relevant one-time commands:
– Extract Prometheus metrics into features using Python script.
– Run ML-based alert validation script to test anomaly-driven remediation enhancement.

---

🧹 CLEANUP / RESET PROCEDURES
Purpose: Reset cluster or monitoring stack for a clean redeployment cycle.

Relevant one-time commands:
– Delete monitoring namespace to clean up all monitoring-related resources.
– Delete the Kind cluster to start fresh for new test iterations.

---

✅ FINAL NOTES
• Always verify Prometheus pod status after applying configurations.
• If Prometheus fails to start, ensure the ServiceAccount file is applied before rollout.
• After any ConfigMap or Secret changes, restart Prometheus and Alertmanager deployments.
• Default service ports are as follows:
– Prometheus: 9090
– Alertmanager: 9093
– Remediator (FastAPI): 8000
– Sample App: 8080
• Maintain strict namespace isolation between modules to prevent resource overlaps.
• This document must remain version-controlled for reproducibility and quick recovery.

---

Maintained by: nrichardrexon
Last Updated: 29 October 2025

---

