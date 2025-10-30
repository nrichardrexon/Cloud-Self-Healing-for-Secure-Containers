import os

# Define the folder structure
folders = [
    "app",
    "monitoring",
    "remediator",
    "scripts",
    "docs"
]

# Create folders if they don't exist
for folder in folders:
    os.makedirs(folder, exist_ok=True)
    print(f"✅ Created folder: {folder}")

print("\n🎉 All folders are ready!")
