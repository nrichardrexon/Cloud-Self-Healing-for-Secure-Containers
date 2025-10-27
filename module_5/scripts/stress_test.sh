#!/bin/bash
# module_5/scripts/stress_test.sh
echo "⚡ Starting Module 5 automated stress tests..."

PY_SCRIPT="fault_injection.py"
SCRIPT_DIR="$(dirname "$0")"

python3 "$SCRIPT_DIR/$PY_SCRIPT"

echo "✅ Module 5 stress tests completed!"
