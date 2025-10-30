# setup_kind.py
import subprocess
import sys
import os

def run_command(cmd):
    """Run shell command and print output."""
    try:
        print(f"Running: {cmd}")
        result = subprocess.run(
            cmd, shell=True, check=True, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error running command:\n{e.output}")
        sys.exit(1)

def install_kind():
    """Install Kind in ~/bin if not already installed."""
    try:
        subprocess.run("kind --version", shell=True, check=True)
        print("✅ Kind already installed.")
    except subprocess.CalledProcessError:
        print("Installing Kind in ~/bin...")
        run_command("mkdir -p ~/bin")
        run_command("curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.25.0/kind-linux-amd64")
        run_command("chmod +x ./kind")
        run_command("mv ./kind ~/bin/")
        # Ensure PATH includes ~/bin
        bashrc_line = "export PATH=$HOME/bin:$PATH"
        bashrc_path = os.path.expanduser("~/.bashrc")
        with open(bashrc_path, "a") as f:
            f.write(f"\n{bashrc_line}\n")
        os.environ["PATH"] = f"{os.path.expanduser('~/bin')}:" + os.environ["PATH"]
        print("✅ Kind installed. PATH updated.")

def create_cluster():
    """Create a Kind cluster."""
    run_command("kind create cluster --name selfhealing-cluster --wait 60s")

def main():
    install_kind()
    create_cluster()
    print("\n✅ Kind cluster setup complete!")
    print("Check with `kubectl cluster-info`")

if __name__ == "__main__":
    main()
