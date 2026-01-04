"""
LeRobot-native recorder for VLA demonstrations.
Saves directly in LeRobot HuggingFace dataset format.
"""

import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# LeRobot dataset import (v0.4+)
LEROBOT_AVAILABLE = False
LeRobotDataset = None

try:
    from lerobot.datasets.lerobot_dataset import LeRobotDataset
    LEROBOT_AVAILABLE = True
    logger.info("LeRobot dataset API loaded")
except ImportError as e:
    logger.warning(f"LeRobot dataset API not available: {e}")


class LeRobotRecorder:
    """Records demonstrations in LeRobot dataset format."""
    
    # Dataset features definition for SO-101 arm
    FEATURES = {
        "observation.images.main": {
            "dtype": "video",
            "shape": (480, 640, 3),
            "names": ["height", "width", "channel"],
        },
        "observation.images.wrist": {
            "dtype": "video",
            "shape": (480, 640, 3),
            "names": ["height", "width", "channel"],
        },
        "observation.state": {
            "dtype": "float32",
            "shape": (6,),
            "names": ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"],
        },
        "action": {
            "dtype": "float32",
            "shape": (6,),
            "names": ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"],
        },
    }
    
    def __init__(self, datasets_dir: str = "datasets"):
        self.datasets_dir = Path(datasets_dir)
        self.datasets_dir.mkdir(parents=True, exist_ok=True)
        
        # Alias for backwards compatibility
        self.dataset_root = self.datasets_dir
        
        self.dataset: Optional[LeRobotDataset] = None
        self.dataset_name: Optional[str] = None
        self.recording = False
        self.thread: Optional[threading.Thread] = None
        
        self.frame_count = 0
        self.episode_count = 0
        
        logger.info(f"LeRobot Recorder initialized. Available: {LEROBOT_AVAILABLE}")
        
    def list_datasets(self):
        """List all recorded datasets."""
        datasets = []
        for d in self.datasets_dir.iterdir():
            if d.is_dir():
                # Check for LeRobot dataset markers
                is_lerobot = (d / "meta").exists() or (d / "data").exists()
                datasets.append({
                    "name": d.name,
                    "path": str(d),
                    "is_lerobot": is_lerobot
                })
        return datasets
        
    def create_dataset(self, name: str):
        """Create a new LeRobot dataset."""
        if not LEROBOT_AVAILABLE:
            return False, "LeRobot not installed on this system"
            
        dataset_path = self.datasets_dir / name
        
        if dataset_path.exists():
            return False, f"Dataset '{name}' already exists"
            
        try:
            # Create LeRobot dataset
            self.dataset = LeRobotDataset.create(
                repo_id=name,
                root=str(self.datasets_dir.resolve()),
                fps=30,
                features=self.FEATURES,
            )
            self.dataset_name = name
            self.episode_count = 0
            
            logger.info(f"Created LeRobot dataset: {name}")
            return True, f"Created dataset: {name}"
            
        except Exception as e:
            logger.error(f"Failed to create dataset: {e}")
            return False, f"Failed to create dataset: {e}"
            
    def load_dataset(self, name: str):
        """Load existing dataset for appending episodes."""
        if not LEROBOT_AVAILABLE:
            return False, "LeRobot not installed"
            
        dataset_path = self.datasets_dir / name
        
        if not dataset_path.exists():
            return False, f"Dataset '{name}' not found"
            
        try:
            self.dataset = LeRobotDataset(str(dataset_path))
            self.dataset_name = name
            self.episode_count = self.dataset.meta.total_episodes if hasattr(self.dataset, 'meta') else 0
            
            logger.info(f"Loaded dataset: {name} ({self.episode_count} episodes)")
            return True, f"Loaded dataset with {self.episode_count} episodes"
            
        except Exception as e:
            logger.error(f"Failed to load dataset: {e}")
            return False, str(e)
            
    def start_recording(self):
        """Start recording a new episode."""
        if not self.dataset:
            return False, "No dataset loaded. Create or load one first."
            
        if self.recording:
            return False, "Already recording"
            
        self.recording = True
        self.frame_count = 0
        self.thread = threading.Thread(target=self._recording_loop, daemon=True)
        self.thread.start()
        
        logger.info("Recording started")
        return True, "Recording started"
        
    def stop_recording(self):
        """Stop recording and save episode."""
        if not self.recording:
            return False, "Not recording"
            
        self.recording = False
        
        if self.thread:
            self.thread.join(timeout=2.0)
            self.thread = None
            
        try:
            # Save the episode
            # Save the episode
            self.dataset.save_episode()
            self.episode_count += 1
            
            # Consolidate to ensure availability
            self.dataset.consolidate()
            
            msg = f"Saved ({self.frame_count} frames)"
            
            # Auto-upload if logged in
            try:
                from huggingface_hub import whoami
                user = whoami()['name']
                target_repo = f"{user}/{self.dataset_name}"
                
                logger.info(f"Auto-uploading to {target_repo}...")
                self.dataset.push_to_hub(target_repo, private=True)
                msg += f" & Uploaded to {target_repo} ☁️"
            except Exception as e_hub:
                logger.warning(f"Auto-upload skipped: {e_hub}")
                msg += " (Local only)"
            
            logger.info(f"Episode saved/consolidated. {msg}")
            return True, msg
            
        except Exception as e:
            logger.error(f"Failed to save episode: {e}")
            return False, str(e)
            
    def finalize_dataset(self):
        """Finalize dataset for training."""
        if not self.dataset:
            return False, "No dataset loaded"
            
        try:
            self.dataset.consolidate()
            logger.info(f"Dataset finalized: {self.dataset_name}")
            return True, f"Dataset ready for training: {self.episode_count} episodes"
            
        except Exception as e:
            logger.error(f"Failed to finalize: {e}")
            return False, str(e)
            
    def _recording_loop(self):
        """Main recording loop - captures frames at ~30Hz."""
        from state import state
        
        target_interval = 1.0 / 30  # 30 FPS
        
        while self.recording:
            start_time = time.time()
            
            try:
                # Get images
                img_main = None
                img_wrist = None
                
                if hasattr(state, 'latest_frame') and state.latest_frame is not None:
                    img_main = state.latest_frame.copy()
                    img_main = cv2.cvtColor(img_main, cv2.COLOR_BGR2RGB)
                    img_main = cv2.resize(img_main, (640, 480))
                else:
                    img_main = np.zeros((480, 640, 3), dtype=np.uint8)
                    
                if hasattr(state, 'latest_frame_right') and state.latest_frame_right is not None:
                    img_wrist = state.latest_frame_right.copy()
                    img_wrist = cv2.cvtColor(img_wrist, cv2.COLOR_BGR2RGB)
                    img_wrist = cv2.resize(img_wrist, (640, 480))
                else:
                    img_wrist = np.zeros((480, 640, 3), dtype=np.uint8)
                    
                # Get arm state
                arm_pos = state.get_arm_positions()
                state_arr = np.array([
                    arm_pos.get('shoulder_pan', 0),
                    arm_pos.get('shoulder_lift', 0),
                    arm_pos.get('elbow_flex', 0),
                    arm_pos.get('wrist_flex', 0),
                    arm_pos.get('wrist_roll', 0),
                    arm_pos.get('gripper', 0)
                ], dtype=np.float32)
                
                # For imitation learning, action = next state (or same as current for simplicity)
                action_arr = state_arr.copy()
                
                # Add frame to dataset
                frame_data = {
                    "observation.images.main": img_main,
                    "observation.images.wrist": img_wrist,
                    "observation.state": state_arr,
                    "action": action_arr,
                }
                
                self.dataset.add_frame(frame_data)
                self.frame_count += 1
                
            except Exception as e:
                logger.error(f"Recording error: {e}")
                
            # Maintain 30Hz
            elapsed = time.time() - start_time
            sleep_time = max(0, target_interval - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)
                
        logger.info(f"Recording loop ended. Frames: {self.frame_count}")
        
    def get_status(self):
        """Get recorder status."""
        return {
            "recording": self.recording,
            "dataset_name": self.dataset_name,
            "episode_count": self.episode_count,
            "frame_count": self.frame_count,
            "lerobot_available": LEROBOT_AVAILABLE
        }
