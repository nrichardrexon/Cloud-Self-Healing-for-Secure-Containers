import subprocess
import sys

# -----------------------------
# Helper function to run commands
# -----------------------------
def run(cmd, description, allow_fail=False):
    print(f"\n➡️  {description}...")
    try:
        subprocess.check_call(cmd, shell=True)
        print(f"✅ Done: {description}")
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Failed: {description}")
        print(f"   {e}")
        if not allow_fail:
            sys.exit(1)

# -----------------------------
# 1. Upgrade pip
# -----------------------------
run(f"{sys.executable} -m pip install --upgrade pip", "Upgrade pip")

# -----------------------------
# 2. Install Python dependencies from requirements.txt
# -----------------------------
run(f"{sys.executable} -m pip install -r requirements.txt", "Install Python dependencies")

# -----------------------------
# 3. Install Python-based tools
# -----------------------------
run(f"{sys.executable} -m pip install bandit", "Install Bandit (Python security linter)", allow_fail=True)
run(f"{sys.executable} -m pip install checkov", "Install Checkov (IaC scanner)", allow_fail=True)

# -----------------------------
# 4. Guidance for non-Python tools
# -----------------------------
print("\nℹ️ Note: Trivy and Gitleaks are not Python packages and must be installed separately.")
print("🔗 Trivy installation: https://github.com/aquasecurity/trivy#installation")
print("🔗 Gitleaks installation: https://github.com/zricethezav/gitleaks#installation")

# -----------------------------
# 5. Install VS Code extensions if possible
# -----------------------------
try:
    subprocess.check_call("code --version", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("\n➡️ VS Code CLI detected. Installing extensions...")
    vscode_extensions = [
        "ms-python.python",
        "ms-python.vscode-pylance",
        "ms-azuretools.vscode-docker",
        "eamodio.gitlens"
    ]
    for ext in vscode_extensions:
        run(f"code --install-extension {ext}", f"Install VS Code extension: {ext}", allow_fail=True)
except subprocess.CalledProcessError:
    print("\n⚠️ VS Code CLI not found. Skipping extension installation.")

# -----------------------------
# 6. Summary
# -----------------------------
print("\n🎉 Setup complete!")
print("Please ensure the following tools are installed manually if required:")
print("🔗 Trivy: https://github.com/aquasecurity/trivy#installation")
print("🔗 Gitleaks: https://github.com/zricethezav/gitleaks#installation")
print("🔗 More info on tools at their GitHub pages.")
