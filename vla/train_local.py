
import sys
import os
from pathlib import Path

# Monkey-patch get_safe_version to bypass Hub validation for local paths
def patch_lerobot():
    try:
        import lerobot.datasets.utils
        
        original_get_safe_version = lerobot.datasets.utils.get_safe_version
        
        def mocked_get_safe_version(repo_id, revision):
            # If repo_id looks like a path (absolute or relative), return revision as-is
            # This bypasses the Hub check
            if "/" in repo_id or "\\" in repo_id or os.path.isabs(repo_id):
                print(f"[Patch] Bypassing Hub check for local path: {repo_id}")
                return revision
            return original_get_safe_version(repo_id, revision)
            
        lerobot.datasets.utils.get_safe_version = mocked_get_safe_version
        print("[Patch] LeRobot Hub validation patched for local datasets.")
        
    except ImportError:
        print("[Patch] Warning: Could not import lerobot.datasets.utils. Patch failed.")
    except Exception as e:
        print(f"[Patch] Warning: Patch failed with error: {e}")

if __name__ == "__main__":
    patch_lerobot()
    
    # Import main training logic after patching
    try:
        from lerobot.scripts.train import train
        # We need to wrap it in draccus just like the real script
        import draccus
        from lerobot.configs.train import TrainConfig
        
        @draccus.wrap()
        def main(cfg: TrainConfig):
            train(cfg)
            
        main()
        
    except ImportError as e:
        print(f"Error: Could not import LeRobot training scripts. {e}")
        sys.exit(1)
