
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
        import lerobot
        from pathlib import Path
        import importlib.util

        # Find train.py relative to lerobot package
        lerobot_path = Path(lerobot.__file__).parent
        train_script_path = lerobot_path / "scripts" / "train.py"
        
        if not train_script_path.exists():
            # Try alternative locations or fallbacks
            print(f"Warning: {train_script_path} not found. Trying to find via site-packages...")
            # Some installs might put scripts elsewhere or name it differently
            # But let's assume standard structure first or fail with clear message
            pass

        print(f"[Patch] Loading training script from: {train_script_path}")
        
        # Load module dynamically
        spec = importlib.util.spec_from_file_location("lerobot_train_script", train_script_path)
        train_module = importlib.util.module_from_spec(spec)
        sys.modules["lerobot_train_script"] = train_module
        spec.loader.exec_module(train_module)
        
        train_func = train_module.train
        
        # We need to wrap it in draccus just like the real script
        import draccus
        from lerobot.configs.train import TrainConfig
        
        @draccus.wrap()
        def main(cfg: TrainConfig):
            train_func(cfg)
            
        main()
        
    except Exception as e:
        print(f"Error: Could not import LeRobot training scripts. {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
