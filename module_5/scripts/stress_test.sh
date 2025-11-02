#!/bin/bash
# ==========================================
# ⚡ Stress Test Script (Module 5)
# ==========================================
# Purpose: Trigger controlled CPU + Memory stress tests using stress-ng.
# ==========================================

echo "⚡ Starting Module 5 automated stress tests..."
SCRIPT_DIR="$(dirname "$0")"

# Duration in seconds (default 60)
DURATION=${1:-60}

echo "🧠 Running CPU and memory stress for ${DURATION}s..."
stress-ng --cpu 2 --vm 2 --vm-bytes 256M --timeout ${DURATION}s --metrics-brief

# Optional: invoke fault injection Python logic
if [ -f "$SCRIPT_DIR/fault_injection.py" ]; then
  echo "🧩 Executing Python-based fault injection logic..."
  python3 "$SCRIPT_DIR/fault_injection.py"
fi

echo "✅ Module 5 stress tests completed!"
