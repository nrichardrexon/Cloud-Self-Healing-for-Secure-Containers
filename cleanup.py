#!/usr/bin/env python3
"""
🧹 Codespace Auto Cleanup Script (Enhanced v2)
---------------------------------------------
Safely reclaims disk space in GitHub Codespaces by cleaning:
- Python, Node, and system caches
- Temporary and log files
- Docker images, containers, and volumes
- Old APT packages and build caches

Includes before/after disk usage comparison.
"""

import os
import subprocess
import shutil
from pathlib import Path

# ==========================
# Utility Functions
# ==========================
def run_cmd(cmd: str, silent: bool = False):
    """Run a shell command safely and return its output."""
    try:
        result = subprocess.run(
            cmd, shell=True, text=True, capture_output=True
        )
        if not silent:
            if result.stdout.strip():
                print(result.stdout.strip())
            if result.stderr.strip():
                print(f"\033[90m{result.stderr.strip()}\033[0m")
        return result.stdout.strip()
    except Exception as e:
        print(f"⚠️ Error running command '{cmd}': {e}")
        return ""

def remove_path(path: Path):
    """Remove file or directory if it exists."""
    try:
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        elif path.is_file():
            path.unlink(missing_ok=True)
    except Exception as e:
        print(f"⚠️ Skipped {path}: {e}")

def print_section(title: str):
    print(f"\n\033[94m# ============================================\033[0m")
    print(f"🧭 {title}")
    print(f"\033[94m# ============================================\033[0m")

# ==========================
# Cleanup Routine
# ==========================
def cleanup_codespace():
    print_section("Starting GitHub Codespace Cleanup")

    print("📊 Checking initial disk usage...")
    before = run_cmd("df -h /workspaces", silent=True)

    # 1️⃣ Python cache cleanup
    print_section("Removing Python caches (__pycache__, *.pyc)")
    for pattern in ["__pycache__", "*.pyc"]:
        for p in Path("/workspaces").rglob(pattern):
            remove_path(p)

    # 2️⃣ Package manager caches
    print_section("Clearing package manager caches (pip, npm, yarn, poetry)")
    cache_dirs = [
        "~/.cache/pip", "~/.npm", "~/.cache/yarn", "~/.cache/pypoetry",
        "~/.cache/matplotlib", "~/.local/share/virtualenvs"
    ]
    for c in cache_dirs:
        remove_path(Path(os.path.expanduser(c)))

    # 3️⃣ Temp directories cleanup
    print_section("Cleaning temporary directories (/tmp, /var/tmp)")
    for tmp_dir in ["/tmp", "/var/tmp"]:
        for p in Path(tmp_dir).glob("*"):
            remove_path(p)

    # 4️⃣ Large log files
    print_section("Deleting large log files (>50MB)")
    for log_file in Path("/workspaces").rglob("*.log"):
        try:
            if log_file.stat().st_size > 50 * 1024 * 1024:
                print(f"🗑 Removing large log: {log_file}")
                remove_path(log_file)
        except FileNotFoundError:
            pass

    # 5️⃣ Docker cleanup
    print_section("Pruning Docker system (images, containers, volumes)")
    run_cmd("docker system prune -af --volumes")

    # 6️⃣ Builder cache cleanup
    print_section("Clearing Docker build cache")
    run_cmd("docker builder prune -af")

    # 7️⃣ APT cleanup
    print_section("Cleaning APT cache and unused packages")
    run_cmd("sudo apt-get clean")
    run_cmd("sudo apt-get autoremove -y")
    run_cmd("sudo apt-get autoclean")

    # 8️⃣ Fix permissions if any issues
    print_section("Fixing potential permission issues")
    run_cmd("sudo chmod -R 777 /tmp /var/tmp /workspaces || true")

    # ==========================
    # Final Summary
    # ==========================
    print_section("Cleanup Summary")
    after = run_cmd("df -h /workspaces", silent=True)
    print("\n📦 Before Cleanup:\n" + before)
    print("\n✅ After Cleanup:\n" + after)
    print("\n🎉 Cleanup complete! Your Codespace should now have more free space.")

# ==========================
# Main Entry
# ==========================
if __name__ == "__main__":
    cleanup_codespace()
