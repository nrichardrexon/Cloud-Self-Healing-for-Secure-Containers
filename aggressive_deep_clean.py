#!/usr/bin/env python3
"""
🚀 Codespace Maximum Safe Cleanup (User-Level)
Aggressively reclaims disk space without requiring sudo.
"""

import os, subprocess, shutil, tarfile
from datetime import datetime
from pathlib import Path

# -------------------------------------------
# Utility Functions
# -------------------------------------------
def run(cmd):
    print(f"➡️ {cmd}")
    subprocess.run(cmd, shell=True, check=False)

def remove(path):
    try:
        if path.exists():
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
            else:
                path.unlink(missing_ok=True)
    except Exception as e:
        print(f"⚠️ Skipped {path}: {e}")

def get_used_space():
    result = subprocess.run("df --output=used -BG /workspaces | tail -1", shell=True, text=True, capture_output=True)
    return float(result.stdout.strip().replace("G", ""))

# -------------------------------------------
# Main Cleanup Steps
# -------------------------------------------
def max_clean():
    print("\n🧹 Starting MAX CLEANUP for Codespace...")
    print("============================================")

    before = get_used_space()
    print(f"📊 Disk used before: {before:.1f} GB\n")

    # 1️⃣ Remove caches
    for path in [
        "~/.cache", "~/.npm", "~/.yarn", "~/.local/share/Trash",
        "/workspaces/__pycache__", "/workspaces/.pytest_cache",
    ]:
        remove(Path(os.path.expanduser(path)))

    # 2️⃣ Delete all Python build artifacts
    print("🧩 Removing __pycache__ and *.pyc files...")
    for ext in ("__pycache__", "*.pyc"):
        for f in Path("/workspaces").rglob(ext):
            remove(f)

    # 3️⃣ Archive & delete large log files (>20MB)
    archive_dir = Path("/workspaces/_log_archive")
    archive_dir.mkdir(exist_ok=True)
    tar_path = archive_dir / f"logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.tar.gz"
    with tarfile.open(tar_path, "w:gz") as tar:
        for f in Path("/workspaces").rglob("*.log"):
            try:
                if f.stat().st_size > 20 * 1024 * 1024:
                    tar.add(f, arcname=f.name)
                    remove(f)
            except FileNotFoundError:
                pass

    # 4️⃣ Remove Docker data aggressively (safe mode)
    print("\n🐳 Cleaning Docker data...")
    run("docker ps -aq | xargs -r docker rm -f")
    run("docker images -q | xargs -r docker rmi -f")
    run("docker system prune -af --volumes")
    run("docker builder prune -af")
    run("docker volume prune -f")

    # 5️⃣ Clean Git garbage
    print("\n🧩 Running Git GC...")
    run("git gc --prune=now --aggressive")

    # 6️⃣ Remove VSCode cache
    print("\n🧰 Removing VSCode & extension caches...")
    for cache_dir in [
        "~/.vscode-server/extensions",
        "~/.vscode-server-insiders/extensions",
        "~/.config/Code",
        "~/.config/Code - OSS",
    ]:
        remove(Path(os.path.expanduser(cache_dir)))

    # 7️⃣ Final check
    after = get_used_space()
    freed = max(before - after, 0)
    print(f"\n✅ Cleanup complete.")
    print(f"📉 Disk before: {before:.1f} GB → after: {after:.1f} GB")
    print(f"💾 Reclaimed: {freed:.2f} GB")
    print("\n🟢 Codespace is optimized and safe to continue.\n")

# -------------------------------------------
if __name__ == "__main__":
    max_clean()
