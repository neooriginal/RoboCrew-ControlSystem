import sys
import os
from pathlib import Path

# Try imports
try:
    from lerobot.common.datasets.lerobot_dataset import LeRobotDataset
except ImportError:
    try:
        from lerobot.datasets.lerobot_dataset import LeRobotDataset
    except ImportError:
        print("Error: Could not import LeRobotDataset")
        sys.exit(1)

from huggingface_hub import whoami

def upload_dataset(dataset_name):
    ds_dir = Path(__file__).parent.parent / "datasets"
    print(f"Looking for dataset '{dataset_name}' in {ds_dir.absolute()}")
    
    # Get Username
    try:
        user_info = whoami()
        username = user_info['name']
    except Exception as e:
        print(f"Error getting HF user: {e}. Please login first.")
        sys.exit(1)

    # Try loading - we don't know if it was saved as 'local/Name' or 'Name'
    ds = None
    
    # Attempt 1: local/Name (Recorder default)
    try:
        print(f"Attempting load with id='local/{dataset_name}'...")
        ds = LeRobotDataset(f"local/{dataset_name}", root=ds_dir)
        print("Loaded successfully as local/")
    except Exception as e1:
        print(f"Failed loading 'local/{dataset_name}': {e1}")
        
        # Attempt 2: Name only
        try:
            print(f"Attempting load with id='{dataset_name}'...")
            ds = LeRobotDataset(dataset_name, root=ds_dir)
            print("Loaded successfully as plain name")
        except Exception as e2:
             print(f"Failed loading '{dataset_name}': {e2}")
             print("Could not load dataset.")
             sys.exit(1)

    target_repo = f"{username}/{dataset_name}"
    print(f"Uploading to Hub: {target_repo}...")
    
    try:
        ds.push_to_hub(target_repo, private=True)
        print(f"SUCCESS: Dataset uploaded to {target_repo}")
    except Exception as e:
        print(f"Upload failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python upload_dataset.py <dataset_name>")
        # Default for debugging
        upload_dataset("Ttest")
    else:
        upload_dataset(sys.argv[1])
