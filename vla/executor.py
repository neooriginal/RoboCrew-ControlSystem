"""
VLA Executor
Handles model inference and robot control using Receding Horizon Control.
"""

import time
import torch
import numpy as np
import cv2
import threading
import logging
from pathlib import Path

from state import state
from .model import SimplePolicy

logger = logging.getLogger(__name__)

class VLAExecutor:
    def __init__(self, models_dir="models"):
        self.models_dir = Path(models_dir)
        self.running = False
        self.thread = None
        self.model = None
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
    def load_model(self, model_name):
        model_path = self.models_dir / f"{model_name}.pth"
        if not model_path.exists():
            return False, "Model not found"
            
        try:
            # Re-init model structure
            self.model = SimplePolicy(chunk_size=10).to(self.device)
            self.model.load_state_dict(torch.load(model_path, map_location=self.device))
            self.model.eval()
            logger.info(f"Loaded model {model_name}")
            return True, "Model loaded"
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False, str(e)

    def start_execution(self, model_name):
        if self.running:
            return False, "Already running"
            
        success, msg = self.load_model(model_name)
        if not success:
            return False, msg
            
        self.running = True
        self.thread = threading.Thread(target=self._execution_loop, daemon=True)
        self.thread.start()
        return True, "Execution started"

    def stop_execution(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
            self.thread = None
        return True

    def _execution_loop(self):
        logger.info("VLA Execution started")
        
        # Temporal Ensembling buffer or just simple Receding Horizon
        # Simple RHC: Predict 10, execute 1-2, predict again.
        
        step_interval = 0.05 # 20Hz control loop target
        
        with torch.no_grad():
            while self.running:
                start_time = time.time()
                
                # 1. Capture State
                if not hasattr(state, 'latest_frame') or state.latest_frame is None:
                    time.sleep(0.01)
                    continue
                    
                img_raw = state.latest_frame.copy()
                qpos_map = state.get_arm_positions()
                
                # Preprocess Image
                img = cv2.resize(img_raw, (224, 224))
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                img_t = torch.from_numpy(img).permute(2, 0, 1).float().unsqueeze(0).to(self.device) / 255.0
                
                # Preprocess State
                qpos = np.array([
                    qpos_map.get('shoulder_pan', 0),
                    qpos_map.get('shoulder_lift', 0),
                    qpos_map.get('elbow_flex', 0),
                    qpos_map.get('wrist_flex', 0),
                    qpos_map.get('wrist_roll', 0),
                    qpos_map.get('gripper', 0)
                ], dtype=np.float32)
                qpos_t = torch.from_numpy(qpos).unsqueeze(0).to(self.device)
                
                # 2. Inference
                # Returns [1, 10, 6]
                actions_chunk = self.model(img_t, qpos_t)
                actions_np = actions_chunk.cpu().numpy()[0] # [10, 6]
                
                # 3. Execute first few actions (Receding Horizon)
                # Execute first 3 steps (approx 150ms) before re-planning
                
                steps_to_exec = 3
                for i in range(steps_to_exec):
                    if not self.running:
                        break
                        
                    action = actions_np[i]
                    
                    # Convert action array back to dict
                    target_pos = {
                        'shoulder_pan': float(action[0]),
                        'shoulder_lift': float(action[1]),
                        'elbow_flex': float(action[2]),
                        'wrist_flex': float(action[3]),
                        'wrist_roll': float(action[4]),
                        'gripper': float(action[5])
                    }
                    
                    # Send to controller
                    if state.controller:
                        try:
                            # Use set_arm_position directly
                            state.controller.set_arm_position(target_pos)
                            state.update_arm_positions(target_pos)
                        except Exception as e:
                            logger.error(f"Control error: {e}")
                            
                    # Wait for next step
                    time.sleep(step_interval)
                
                # Adjust loop timing if inference was fast
                elapsed = time.time() - start_time
                if elapsed < 0.1: # Min inference time cap
                     time.sleep(0.01)

        logger.info("VLA Execution stopped")
