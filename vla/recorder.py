"""
VLA Data Recorder
Handles recording of camera frames and robot state.
"""

import os
import time
import json
import cv2
import threading
import logging
import shutil
from pathlib import Path
from datetime import datetime
from state import state

logger = logging.getLogger(__name__)

class VLARecorder:
    def __init__(self, dataset_dir="datasets"):
        self.dataset_root = Path(dataset_dir)
        self.dataset_root.mkdir(parents=True, exist_ok=True)
        
        self.recording = False
        self.current_dataset_path = None
        self.current_task_name = None
        self.frame_count = 0
        self.record_thread = None
        self.lock = threading.Lock()
        
        # Recording rate (30Hz target)
        self.interval = 1.0 / 30.0

    def start_recording(self, dataset_name=None):
        with self.lock:
            if self.recording:
                return False, "Already recording"
                
            if not dataset_name:
                dataset_name = f"recording_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Sanitize name
            dataset_name = "".join(c for c in dataset_name if c.isalnum() or c in ('_', '-'))
            
            # Create task directory if not exists
            task_dir = self.dataset_root / dataset_name
            task_dir.mkdir(parents=True, exist_ok=True)
            
            # Create unique episode directory
            episode_name = f"episode_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.current_dataset_path = task_dir / episode_name
            
            try:
                self.current_dataset_path.mkdir(parents=True)
                (self.current_dataset_path / "images_main").mkdir()
                (self.current_dataset_path / "images_wrist").mkdir()
            except Exception as e:
                return False, f"Failed to create directory: {e}"
                
            self.recording = True
            self.frame_count = 0
            self.current_task_name = dataset_name
            
            self.record_thread = threading.Thread(target=_record_loop, args=(self,), daemon=True)
            self.record_thread.start()
            
            logger.info(f"Started recording: {dataset_name}/{episode_name}")
            return True, f"{dataset_name}/{episode_name}"

    def stop_recording(self):
        with self.lock:
            if not self.recording:
                return False, "Not recording"
            
            self.recording = False
            
        if self.record_thread:
            self.record_thread.join(timeout=1.0)
            self.record_thread = None
            
        logger.info(f"Stopped recording. Total frames: {self.frame_count}")
        return True, self.frame_count

    def get_status(self):
        return {
            "recording": self.recording,
            "dataset": self.current_task_name if self.current_task_name else None,
            "episode": self.current_dataset_path.name if self.current_dataset_path else None,
            "frames": self.frame_count
        }
        
    def discard_current(self):
        """Stop and delete the current recording."""
        if self.recording:
            self.stop_recording()
            
        if self.current_dataset_path and self.current_dataset_path.exists():
            try:
                shutil.rmtree(self.current_dataset_path)
                logger.info("Discarded current dataset")
                self.current_dataset_path = None
                return True
            except Exception as e:
                logger.error(f"Failed to discard dataset: {e}")
                return False
        return False

    def delete_last_episode(self):
        """Delete the most recently recorded episode if it exists."""
        # 1. If currently recording, discard it.
        if self.recording:
            return self.discard_current()
            
        # 2. If valid dataset path (episode) is set, delete it.
        if self.current_dataset_path and self.current_dataset_path.exists():
             try:
                shutil.rmtree(self.current_dataset_path)
                logger.info(f"Deleted last episode: {self.current_dataset_path.name}")
                self.current_dataset_path = None
                self.frame_count = 0
                return True
             except Exception as e:
                logger.error(f"Failed to delete episode: {e}")
                return False
        return False


def _record_loop(recorder):
    """Background loop for recording data."""
    jsonl_path = recorder.current_dataset_path / "data.jsonl"
    
    logger.info("Recording loop started")
    
    with open(jsonl_path, "a") as f:
        while recorder.recording:
            start_time = time.time()
            
            # Capture state snapshot
            # We copy specific values to avoid race conditions or mutating state
            current_state = {
                "timestamp": start_time,
                "frame_id": recorder.frame_count,
            }
            
            # 1. Get Frames (Copy to avoid mutation during save)
            img_main = None
            img_wrist = None
            
            if hasattr(state, 'latest_frame') and state.latest_frame is not None:
                img_main = state.latest_frame.copy()
            
            if hasattr(state, 'latest_frame_right') and state.latest_frame_right is not None:
                img_wrist = state.latest_frame_right.copy()
                
            # 2. Get Arm Position
            # Currently using state.get_arm_positions() which returns the latest known positions.
            arm_pos = state.get_arm_positions()
            current_state["qpos"] = arm_pos
            
            # 3. Save Images
            # Use threading count to ensure unique filenames
            fid = recorder.frame_count
            
            main_filename = f"frame_{fid:06d}.jpg"
            wrist_filename = f"wrist_{fid:06d}.jpg"
            
            # Save Main Camera
            if img_main is not None:
                path_main = recorder.current_dataset_path / "images_main" / main_filename
                try:
                    # Async write or fast write? 
                    # cv2.imwrite is blocking but usually fast enough for 30fps on small resolutions.
                    # If it lags, we might need a queue. For now keep simple.
                    cv2.imwrite(str(path_main), img_main)
                    current_state["image_main"] = main_filename
                except Exception as e:
                    logger.error(f"Failed to save main image: {e}")
            
            # Save Wrist Camera
            if img_wrist is not None:
                path_wrist = recorder.current_dataset_path / "images_wrist" / wrist_filename
                try:
                    cv2.imwrite(str(path_wrist), img_wrist)
                    current_state["image_wrist"] = wrist_filename
                except Exception as e:
                    logger.error(f"Failed to save wrist image: {e}")
            
            # 4. Save Jsonl Entry
            
            if img_main is not None:
                f.write(json.dumps(current_state) + "\n")
                f.flush() # Ensure it hits disk
                recorder.frame_count += 1
            
            # Maintain frequency
            elapsed = time.time() - start_time
            sleep_time = recorder.interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

