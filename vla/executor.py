"""
VLA Executor
Handles model inference and robot control using Diffusion Policy.
Includes Normalization (MinMax) and Safety Limits (Speed Clamping).
"""

import time
import torch
import numpy as np
import cv2
import threading
import logging
import json
from pathlib import Path
from collections import deque

from state import state
from .model import DiffusionPolicy

logger = logging.getLogger(__name__)

class VLAExecutor:
    def __init__(self, models_dir="models"):
        self.models_dir = Path(models_dir)
        self.running = False
        self.thread = None
        self.model = None
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # Normalization Stats
        self.stats = None
        
        # Safety / Smoothing
        self.max_delta = 0.1 # Max radians change per step (~2.0 rad/s at 20Hz). Lower = safer/smoother.
        
        # History Buffer
        # Stores last N obs: (img_main, img_wrist, qpos)
        self.history_len = 2
        self.history = deque(maxlen=self.history_len)
        
    def load_model(self, model_name):
        model_path = self.models_dir / f"{model_name}.pth"
        if not model_path.exists():
            return False, "Model not found"
            
        # Try load stats
        # Try load stats
        # logic: 1. Try exact match "{model_name}_stats.json"
        #        2. Try stripping epoch suffix (e.g. "_ep50")
        stats_candidates = [
            self.models_dir / f"{model_name}_stats.json"
        ]
        
        # Regex to strip _epXX
        import re
        base_name = re.sub(r'_ep\d+$', '', model_name)
        if base_name != model_name:
            stats_candidates.append(self.models_dir / f"{base_name}_stats.json")
            
        loaded_stats = False
        for stats_path in stats_candidates:
            if stats_path.exists():
                try:
                    with open(stats_path, 'r') as f:
                        self.stats = json.load(f)
                    # Convert to numpy
                    self.stats["qpos_min"] = np.array(self.stats["qpos_min"], dtype=np.float32)
                    self.stats["qpos_max"] = np.array(self.stats["qpos_max"], dtype=np.float32)
                    logger.info(f"Loaded normalization stats from {stats_path.name}")
                    loaded_stats = True
                    break
                except Exception as e:
                    logger.error(f"Failed to load stats from {stats_path}: {e}")
        
        if not loaded_stats:
            self.stats = None
            logger.warning(f"No normalization stats found! Checked: {[p.name for p in stats_candidates]}")

        try:
            # Re-init model structure
            self.model = DiffusionPolicy().to(self.device)
            self.model.load_state_dict(torch.load(model_path, map_location=self.device))
            self.model.eval()
            logger.info(f"Loaded diffusion model {model_name}")
            return True, "Model loaded"
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False, str(e)

    def _normalize_qpos(self, qpos):
        if self.stats is None:
            return qpos
        mn = self.stats["qpos_min"]
        mx = self.stats["qpos_max"]
        # Scale to [-1, 1]
        norm = (qpos - mn) / (mx - mn)
        return norm * 2 - 1

    def _unnormalize_qpos(self, qpos_norm):
        if self.stats is None:
            return qpos_norm
        mn = self.stats["qpos_min"]
        mx = self.stats["qpos_max"]
        # Scale from [-1, 1] back to [0, 1] then to Range
        norm = (qpos_norm + 1) / 2
        return norm * (mx - mn) + mn

    def start_execution(self, model_name):
        if self.running:
            return False, "Already running"
            
        success, msg = self.load_model(model_name)
        if not success:
            return False, msg
            
        self.running = True
        self.history.clear()
        self.thread = threading.Thread(target=self._execution_loop, daemon=True)
        self.thread.start()
        return True, "Execution started"

    def stop_execution(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
            self.thread = None
        return True

    def _prepare_obs(self):
        """Fetches current observation and formats it."""
        if not hasattr(state, 'latest_frame') or state.latest_frame is None:
            return None
            
        # 1. Main Camera
        img_raw = state.latest_frame.copy()
        img = cv2.resize(img_raw, (224, 224))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # 2. Wrist Camera
        img_wrist = np.zeros_like(img)
        if hasattr(state, 'latest_frame_right') and state.latest_frame_right is not None:
             img_w_raw = state.latest_frame_right.copy()
             img_w_raw = cv2.resize(img_w_raw, (224, 224))
             img_wrist = cv2.cvtColor(img_w_raw, cv2.COLOR_BGR2RGB)
        
        # 3. State
        qpos_map = state.get_arm_positions()
        qpos = np.array([
            qpos_map.get('shoulder_pan', 0),
            qpos_map.get('shoulder_lift', 0),
            qpos_map.get('elbow_flex', 0),
            qpos_map.get('wrist_flex', 0),
            qpos_map.get('wrist_roll', 0),
            qpos_map.get('gripper', 0)
        ], dtype=np.float32)
        
        return (img, img_wrist, qpos)

    def _execution_loop(self):
        logger.info("VLA Execution started (Diffusion Policy)")
        
        step_interval = 0.05 # 20Hz control loop target
        
        # Warmup history buffer
        logger.info("Warming up history buffer...")
        while self.running and len(self.history) < self.history_len:
             obs = self._prepare_obs()
             if obs:
                 self.history.append(obs)
             time.sleep(0.05)
             
        logger.info("Buffer ready. Starting inference loop.")
        
        with torch.no_grad():
            while self.running:
                start_time = time.time()
                
                # 1. Update Current Observation
                obs = self._prepare_obs()
                if obs:
                    self.history.append(obs)
                else:
                    time.sleep(0.01)
                    continue
                    
                # 2. Tensorize History
                imgs_main_list = []
                imgs_wrist_list = []
                qpos_list = []
                
                for item in self.history:
                    # item[2] is raw qpos. Need to normalize it.
                    norm_qpos = self._normalize_qpos(item[2])
                    
                    img_m_t = torch.from_numpy(item[0]).permute(2,0,1).float() / 255.0
                    img_w_t = torch.from_numpy(item[1]).permute(2,0,1).float() / 255.0
                    qpos_t = torch.from_numpy(norm_qpos)
                    
                    imgs_main_list.append(img_m_t)
                    imgs_wrist_list.append(img_w_t)
                    qpos_list.append(qpos_t)
                    
                # Stack History
                t_main = torch.stack(imgs_main_list) # [Hist, C, H, W]
                t_wrist = torch.stack(imgs_wrist_list) # [Hist, C, H, W]
                t_qpos = torch.stack(qpos_list) # [Hist, 6]
                
                # Stack Cameras -> [2, Hist, C, H, W]
                t_images = torch.stack([t_main, t_wrist])
                
                # Add Batch Dim -> [1, 2, Hist, C, H, W]
                batch_images = t_images.unsqueeze(0).to(self.device)
                batch_state = t_qpos.unsqueeze(0).to(self.device)
                
                # 3. Diffusion Inference
                # Returns [1, 10, 6] (Normalized Action Chunk)
                actions_chunk = self.model.sample(batch_images, batch_state)
                norm_actions_np = actions_chunk.cpu().numpy()[0] # [10, 6]
                
                # 4. Execute (Receding Horizon)
                if self.running:
                    # Take first action
                    norm_action = norm_actions_np[0]
                    
                    # Un-normalize
                    target_action = self._unnormalize_qpos(norm_action)
                    
                    # Safety: Clamp max delta from current position
                    # We know current position is obs[2] (raw)
                    current_pos = obs[2]
                    delta = target_action - current_pos
                    
                    # DEBUG LOGGING (Throttle to ~2Hz)
                    if int(time.time() * 2) % 2 == 0:  # simplistic throttle
                        logger.info(f"--- DEBUG STEP ---")
                        logger.info(f"Current: {np.round(current_pos, 3)}")
                        logger.info(f"Model Raw: {np.round(norm_action, 3)}")
                        logger.info(f"Target: {np.round(target_action, 3)}")
                        logger.info(f"Delta: {np.round(delta, 3)}")
                        if self.stats:
                            logger.info(f"Stats Range: {np.round(self.stats['qpos_max'] - self.stats['qpos_min'], 3)}")
                    
                    # Clamp magnitude
                    delta = np.clip(delta, -self.max_delta, self.max_delta)
                    safe_action = current_pos + delta
                    
                    target_pos = {
                        'shoulder_pan': float(safe_action[0]),
                        'shoulder_lift': float(safe_action[1]),
                        'elbow_flex': float(safe_action[2]),
                        'wrist_flex': float(safe_action[3]),
                        'wrist_roll': float(safe_action[4]),
                        'gripper': float(safe_action[5])
                    }
                    
                    if state.controller:
                        try:
                            state.controller.set_arm_position(target_pos)
                            state.update_arm_positions(target_pos)
                        except Exception as e:
                            logger.error(f"Control error: {e}")
                            
                # Wait remainder of cycle
                elapsed = time.time() - start_time
                sleep_time = max(0, step_interval - elapsed)
                if sleep_time > 0:
                    time.sleep(sleep_time)

        logger.info("VLA Execution stopped")
