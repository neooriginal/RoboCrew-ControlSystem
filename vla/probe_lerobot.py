
import sys
import os
from pathlib import Path

# Try imports
try:
    print("Attempting imports...")
    from lerobot.common.datasets.lerobot_dataset import LeRobotDataset
    from lerobot.common.policies.act.configuration_act import ACTConfig
    from lerobot.common.policies.act.modeling_act import ACTPolicy
    print("Imports success (common path)")
except ImportError:
    try:
        from lerobot.datasets.lerobot_dataset import LeRobotDataset
        from lerobot.policies.act.configuration_act import ACTConfig
        from lerobot.policies.act.modeling_act import ACTPolicy
        print("Imports success (root path)")
    except ImportError as e:
        print(f"Imports failed: {e}")
        # Identify available modules
        import lerobot
        print(f"LeRobot found at: {lerobot.__file__}")

def test_local_dataset(root_path, repo_id):
    print(f"\nTesting local dataset load: {root_path} ({repo_id})")
    try:
        # Try loading without repo_id if possible, or with local/ prefix
        ds = LeRobotDataset(root=root_path, repo_id=repo_id)
        print("Success: LeRobotDataset instantiated")
        print(f"Stats: {ds.stats}")
    except Exception as e:
        print(f"Failed to instantiate: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 2:
        root = sys.argv[1]
        name = sys.argv[2]
        test_local_dataset(root, name)
    else:
        print("Usage: python probe.py <root> <repo_id>")
