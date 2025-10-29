#!/usr/bin/env python3
"""
🧹 Codespace Auto Cleanup Script
Cleans up caches, temp files, large logs, and old Docker data
to free up disk space inside GitHub Codespaces.
"""

import os
import subprocess
import shutil
from pathlib import Path

def run_cmd(cmd):
    """Run a shell command safely and return output."""
    try:
        result = subprocess.run(cmd, shell=True, text=True, capture_output=True)
        if result.stdout:
            print(result.stdout.strip())
        if result.stderr:
            print(result.stderr.strip())
    except Exception as e:
        print(f"⚠️ Error running command: {cmd}\n{e}")

def remove_path(path: Path):
    """Remove file or directory if it exists."""
    try:
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        elif path.is_file():
            path.unlink(missing_ok=True)
    except Exception as e:
        print(f"⚠️ Skipped {path}: {e}")

def cleanup_codespace():
    print("🧹 Starting cleanup of GitHub Codespace...")

    # 1️⃣ Remove Python cache files
    print("➡️ Removing __pycache__ and *.pyc files...")
    for pattern in ["__pycache__", "*.pyc"]:
        for p in Path("/workspaces").rglob(pattern):
            remove_path(p)

    # 2️⃣ Remove Pip, NPM, and Yarn caches
    print("➡️ Clearing package manager caches...")
    for cache_path in ["~/.cache/pip", "~/.npm", "~/.cache/yarn"]:
        remove_path(Path(os.path.expanduser(cache_path)))

    # 3️⃣ Clean temporary directories
    print("➡️ Cleaning temporary directories...")
    for tmp_dir in ["/tmp", "/var/tmp"]:
        for p in Path(tmp_dir).glob("*"):
            remove_path(p)

    # 4️⃣ Remove large log files (>50MB)
    print("➡️ Deleting large log files (>50MB)...")
    for log_file in Path("/workspaces").rglob("*.log"):
        try:
            if log_file.stat().st_size > 50 * 1024 * 1024:
                remove_path(log_file)
        except FileNotFoundError:
            pass

    # 5️⃣ Docker system prune
    print("➡️ Pruning Docker data (may take a few seconds)...")
    run_cmd("docker system prune -af --volumes")

    # 6️⃣ Show disk usage summary
    print("\n✅ Cleanup complete. Current disk usage:")
    run_cmd("df -h /workspaces")

if __name__ == "__main__":
    cleanup_codespace()
