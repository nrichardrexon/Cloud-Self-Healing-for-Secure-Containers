# Module 5 – Fault Injection & Testing

## Purpose
Inject controlled faults into Remediator pods to validate the self-healing pipeline.

## Scripts
- `scripts/fault_injection.py` – Python CLI for pod-level fault injection.
- `scripts/stress_test.sh` – Bash wrapper for quick stress runs.

## Example Usage
```bash
# List target pods
python3 scripts/fault_injection.py list

# Kill pods
python3 scripts/fault_injection.py kill

# Stress CPU for 15 seconds
python3 scripts/fault_injection.py cpu 15

# Stress Memory for 200MB for 20 seconds
python3 scripts/fault_injection.py mem 200 20
