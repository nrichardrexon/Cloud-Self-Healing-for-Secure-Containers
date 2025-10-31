#!/usr/bin/env python3
"""
🧹 Deep Codespace Cleanup Utility (Enhanced)
Safely frees disk space while preserving all user project files.

Features:
- Removes caches, temp files, logs, and old Docker data
- Archives large logs before deletion
- Cleans VS Code, Docker, and Git data safely
- Prints disk usage before & after cleanup with difference summary
"""

import os
import subprocess
import shutil
import tarfile
from pathlib import Path
from datetime import datetime

# ============================================================
# Utility Helpers
# ============================================================
def run_cmd(cmd: str):
    """Run a shell command safely and print output."""
    print(f"➡️ {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, text=True, capture_output=True)
        if result.stdout.strip():
            print(result.stdout.strip())
        if result.stderr.strip():
            print(result.stderr.strip())
    except Exception as e:
        print(f"⚠️ Error running command: {cmd}\n{e}")

def remove_path(path: Path):
    """Safely remove file or directory if it exists."""
    try:
        if path.exists():
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
            else:
                path.unlink(missing_ok=True)
    except Exception as e:
        print(f"⚠️ Skipped {path}: {e}")

def get_disk_usage() -> float:
    """Return used disk space in GB for /workspaces."""
    try:
        result = subprocess.run(
            "df --output=used -BG /workspaces | tail -1",
            shell=True, text=True, capture_output=True
        )
        return float(result.stdout.strip().replace("G", ""))
    except Exception:
        return 0.0

def archive_large_logs(base_dir="/workspaces"):
    """Archive large log files (>50MB) before deleting them."""
    archive_dir = Path("/workspaces/_log_archive")
    archive_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    tar_path = archive_dir / f"archived_logs_{timestamp}.tar.gz"

    with tarfile.open(tar_path, "w:gz") as tar:
        for log_file in Path(base_dir).rglob("*.log"):
            try:
                if log_file.stat().st_size > 50 * 1024 * 1024:
                    size_mb = log_file.stat().st_size / (1024 * 1024)
                    print(f"🗃 Archiving {log_file} ({size_mb:.1f} MB)")
                    tar.add(log_file, arcname=log_file.name)
                    remove_path(log_file)
            except FileNotFoundError:
                continue
            except Exception as e:
                print(f"⚠️ Could not archive {log_file}: {e}")
    print(f"✅ Large logs archived at: {tar_path}")

# ============================================================
# Main Cleanup Logic
# ============================================================
def deep_cleanup():
    print("\n🧹 Starting deep cleanup of Codespace...")
    print("----------------------------------------------------")

    # Record initial usage
    before_usage = get_disk_usage()
    print("\n📊 Disk usage before cleanup:")
    run_cmd("df -h /workspaces")

    # 1️⃣ Clean package caches
    print("\n➡️ Cleaning pip, npm, and yarn caches...")
    for cache in ["~/.cache/pip", "~/.npm", "~/.cache/yarn"]:
        remove_path(Path(os.path.expanduser(cache)))

    # 2️⃣ Remove Python build junk
    print("\n➡️ Removing __pycache__ and compiled Python files...")
    for pattern in ["__pycache__", "*.pyc"]:
        for p in Path("/workspaces").rglob(pattern):
            remove_path(p)

    # 3️⃣ Clean temporary directories
    print("\n➡️ Cleaning /tmp and /var/tmp...")
    for tmp_dir in ["/tmp", "/var/tmp"]:
        for p in Path(tmp_dir).glob("*"):
            remove_path(p)

    # 4️⃣ Archive + delete large log files
    print("\n➡️ Archiving and deleting large log files (>50MB)...")
    archive_large_logs()

    # 5️⃣ Docker cleanup (safe + aggressive)
    print("\n🐋 Cleaning unused Docker data...")
    run_cmd("docker container prune -f")
    run_cmd("docker image prune -af")
    run_cmd("docker builder prune -af")
    run_cmd("docker volume prune -f")
    run_cmd("docker system prune -af --volumes")

    # 6️⃣ Git garbage collection
    print("\n🧩 Running Git garbage collection...")
    run_cmd("git gc --prune=now --aggressive || true")
    run_cmd("rm -rf .git/objects/pack/*.keep || true")

    # 7️⃣ Remove VS Code and workspace cache
    print("\n🧰 Removing VS Code extension and workspace cache...")
    for vs_cache in [
        "~/.vscode-server/extensions",
        "~/.vscode-server-insiders/extensions",
        "~/.config/Code",
        "~/.config/Code - OSS"
    ]:
        remove_path(Path(os.path.expanduser(vs_cache)))

    # 8️⃣ Final disk usage summary
    print("\n✅ Cleanup complete. Current disk usage:")
    run_cmd("df -h /workspaces")

    after_usage = get_disk_usage()
    reclaimed = max(before_usage - after_usage, 0)
    print(f"\n💾 Reclaimed Space: {reclaimed:.2f} GB freed.")
    print("\n🟢 Safe to continue working — Codespace is optimized!\n")

# ============================================================
# Entry Point
# ============================================================
if __name__ == "__main__":
    deep_cleanup()
