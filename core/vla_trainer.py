"""
VLA Trainer Module
Handles recording of VR teleop sessions into LeRobotDataset format and managing local datasets.
"""

import time
import shutil
import logging
import threading
import numpy as np
import cv2
from pathlib import Path
from typing import Dict, Optional, List
import datetime
import json

# Try to import LeRobot dependencies
try:
    from lerobot.common.datasets.lerobot_dataset import LeRobotDataset
    LEROBOT_AVAILABLE = True
except ImportError:
    LEROBOT_AVAILABLE = False
    print("Warning: lerobot not installed. VLA features will be disabled.")

from config import (
    VLA_ARM_CAMERA_PORT,
    VLA_CAMERA_WIDTH,
    VLA_CAMERA_HEIGHT,
    VLA_CAMERA_FPS,
    VLA_DATASETS_DIR
)
from state import state

logger = logging.getLogger(__name__)

class VLADatasetRecorder:
    """Records VR teleop demonstrations into LeRobot dataset format."""
    
    def __init__(self, dataset_name: str, task_description: str):
        self.dataset_name = dataset_name
        self.task_description = task_description
        self.is_recording = False
        self.current_episode_index = 0
        self.frame_index = 0
        
        # Buffer for current episode data
        self.episode_buffer = {
            "observation.state": [],
            "observation.images.arm_camera": [],
            "action": [],
            "timestamp": []
        }
        
        # Initialize camera
        self.camera = None
        self._init_camera()
        
        # Ensure dataset directory exists
        self.dataset_path = VLA_DATASETS_DIR / dataset_name
        self.dataset_path.mkdir(parents=True, exist_ok=True)
        
        # Setup LeRobot Dataset if available
        self.dataset = None
        if LEROBOT_AVAILABLE:
            try:
                # We initialize LeRobotDataset. 
                # Note: creating a new dataset from scratch locally usually involves 
                # collecting data first, then formatting it. 
                # Here we'll buffer episodes locally and then write them using LeRobot utilities 
                # or simplified custom writers if LeRobot's realtime API is complex.
                # For simplicity in this 'from scratch' implementation, we will use a 
                # structure compatible with LeRobot and convert/save at the end of episode.
                pass 
            except Exception as e:
                logger.error(f"Failed to init LeRobot dataset: {e}")

    def _init_camera(self):
        try:
            self.camera = cv2.VideoCapture(VLA_ARM_CAMERA_PORT)
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, VLA_CAMERA_WIDTH)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, VLA_CAMERA_HEIGHT)
            self.camera.set(cv2.CAP_PROP_FPS, VLA_CAMERA_FPS)
            self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except Exception as e:
            logger.error(f"VLA Camera init failed: {e}")

    def start_episode(self, task_description: str = None):
        """Start recording a new episode."""
        if task_description:
            self.task_description = task_description
            
        self.is_recording = True
        self.frame_index = 0
        self.episode_buffer = {
            "observation.state": [],
            "observation.images.arm_camera": [],
            "action": [],
            "timestamp": []
        }
        self.start_time = time.time()
        logger.info(f"Started VLA episode {self.current_episode_index}")

    def capture_frame(self, arm_state: Dict, action: Dict):
        """
        Capture a single frame of data.
        Called typically at 30Hz from the VR loop.
        """
        if not self.is_recording:
            return

        # 1. Capture Camera Frame
        ret, frame = self.camera.read()
        if not ret:
            logger.warning("VLA Camera capture failed")
            # Create black frame as fallback to keep sync
            frame = np.zeros((VLA_CAMERA_HEIGHT, VLA_CAMERA_WIDTH, 3), dtype=np.uint8)

        # 2. Format State (6 DoF + Gripper)
        # Order: shoulder_pan, shoulder_lift, elbow_flex, wrist_flex, wrist_roll, gripper
        current_state = np.array([
            arm_state.get('shoulder_pan', 0),
            arm_state.get('shoulder_lift', 0),
            arm_state.get('elbow_flex', 0),
            arm_state.get('wrist_flex', 0),
            arm_state.get('wrist_roll', 0),
            arm_state.get('gripper', 0)
        ], dtype=np.float32)

        # 3. Format Action
        # For teleop, action is typically the NEXT state or the command sent.
        # In this simplistic recorder, we'll use the target position sent by VR as the 'action'
        # Or if action is delta, we might need to convert. 
        # Assuming 'action' arg contains the target joint angles.
        current_action = np.array([
            action.get('shoulder_pan', 0),
            action.get('shoulder_lift', 0),
            action.get('elbow_flex', 0),
            action.get('wrist_flex', 0),
            action.get('wrist_roll', 0),
            action.get('gripper', 0)
        ], dtype=np.float32)

        # 4. Store in buffer
        self.episode_buffer["observation.state"].append(current_state)
        self.episode_buffer["observation.images.arm_camera"].append(frame)
        self.episode_buffer["action"].append(current_action)
        self.episode_buffer["timestamp"].append(time.time() - self.start_time)
        
        self.frame_index += 1

    def end_episode(self):
        """Save the current episode to disk."""
        self.is_recording = False
        if self.frame_index < 10:
            logger.warning("Episode too short, discarding")
            return

        logger.info(f"Saving episode {self.current_episode_index} with {self.frame_index} frames...")
        
        # Save to temporary directory structure first
        # Ideally we use LeRobotDataset.add_episode if we had it fully integrated 
        # But for now, let's save raw files that we can convert or load.
        # Structure:
        # dataset_root/
        #   videos/
        #     episode_000000.mp4
        #   data/
        #     episode_000000.parquet
        
        timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        ep_idx = self.current_episode_index
        
        # 1. Save Video
        video_dir = self.dataset_path / "videos"
        video_dir.mkdir(exist_ok=True)
        video_path = video_dir / f"episode_{ep_idx:06d}.mp4"
        
        self._save_video(self.episode_buffer["observation.images.arm_camera"], video_path)
        
        # 2. Save Data (Parquet or NPZ for now, to be robust)
        # Using simple JSON/CSV for basic portability if Parquet library issues on Pi
        # But prefer Parquet if possible.
        data_dir = self.dataset_path / "data"
        data_dir.mkdir(exist_ok=True)
        
        # Flatten data for saving
        # Here we just save a simple dictionary pickle/numpy for now to speed up implementation
        # A full LeRobot conversion step can happen later or we can implement parquet writing here.
        # Let's write a simple JSONL or NPY for the metadata to ensure Pi compatibility.
        
        episode_data = {
            "state": [s.tolist() for s in self.episode_buffer["observation.state"]],
            "action": [a.tolist() for a in self.episode_buffer["action"]],
            "timestamp": self.episode_buffer["timestamp"],
            "task": self.task_description
        }
        
        data_path = data_dir / f"episode_{ep_idx:06d}.json"
        with open(data_path, 'w') as f:
            json.dump(episode_data, f)
            
        self.current_episode_index += 1
        logger.info(f"Episode {ep_idx} saved.")

    def cancel_episode(self):
        """Discard current episode."""
        self.is_recording = False
        logger.info("Episode cancelled/discarded.")
        self.episode_buffer = {}

    def _save_video(self, frames, path):
        if not frames:
            return
            
        height, width, layers = frames[0].shape
        # Use mp4v or h264 if available
        fourcc = cv2.VideoWriter_fourcc(*'mp4v') 
        out = cv2.VideoWriter(str(path), fourcc, VLA_CAMERA_FPS, (width, height))
        
        for frame in frames:
            out.write(frame)
        out.release()
        
    def close(self):
        if self.camera:
            self.camera.release()


class VLADatasetManager:
    """Manages local datasets."""
    
    @staticmethod
    def list_datasets() -> List[Dict]:
        if not VLA_DATASETS_DIR.exists():
            return []
            
        datasets = []
        for d in VLA_DATASETS_DIR.iterdir():
            if d.is_dir():
                # Count episodes (json files in data/)
                data_dir = d / "data"
                count = len(list(data_dir.glob("*.json"))) if data_dir.exists() else 0
                
                # Setup zip export path check
                zip_path = d.with_suffix('.zip')
                has_export = zip_path.exists()
                
                datasets.append({
                    "name": d.name,
                    "episodes": count,
                    "path": str(d),
                    "has_export": has_export
                })
        return datasets

    @staticmethod
    def export_dataset(name: str) -> Optional[str]:
        """Zip the dataset for export."""
        src = VLA_DATASETS_DIR / name
        if not src.exists():
            return None
            
        output_path = VLA_DATASETS_DIR / name  # shutil.make_archive adds .zip
        archive = shutil.make_archive(str(output_path), 'zip', str(src))
        return archive

    @staticmethod
    def delete_dataset(name: str):
        path = VLA_DATASETS_DIR / name
        if path.exists():
            shutil.rmtree(path)
        
        # Also clean up zip
        zip_path = VLA_DATASETS_DIR / f"{name}.zip"
        if zip_path.exists():
            zip_path.unlink()
