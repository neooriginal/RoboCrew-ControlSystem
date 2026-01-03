"""
VLA Dataset Loader
Loads image-action pairs from the recorded dataset (multi-episode).
Updated for Diffusion Policy: Returns history of observations.
"""

import json
import torch
from torch.utils.data import Dataset
from pathlib import Path
import cv2
import numpy as np
import logging

logger = logging.getLogger(__name__)

class VLADataset(Dataset):
    def __init__(self, dataset_path, sequence_length=10, history_length=2):
        self.root = Path(dataset_path)
        self.sequence_length = sequence_length # Future horizon
        self.history_length = history_length   # Past context
        
        self.episodes = [] # List of (episode_path, start_idx, length)
        self.global_entries = [] # Map global_idx -> (episode_idx, local_idx)
        
        # Discover episodes
        if not self.root.exists():
            raise FileNotFoundError(f"Dataset root {dataset_path} not found")
            
        episode_dirs = sorted([d for d in self.root.iterdir() if d.is_dir() and d.name.startswith("episode_")])
        
        if not episode_dirs:
            # Fallback for old flat structure (backward compatibility)
            if (self.root / "data.jsonl").exists():
                episode_dirs = [self.root]
                
        for ep_dir in episode_dirs:
            self._load_episode(ep_dir)
            
        print(f"Loaded {len(self.global_entries)} samples from {len(self.episodes)} episodes in {dataset_path}")

    def _load_episode(self, ep_dir):
        jsonl_path = ep_dir / "data.jsonl"
        if not jsonl_path.exists():
            return
            
        entries = []
        with open(jsonl_path, "r") as f:
            for line in f:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        
        if not entries:
            return
            
        # Ensure enough frames for sequence
        # We need history_length frames before, and sequence_length frames after
        # But we can pad the start.
        valid_samples = max(0, len(entries) - self.sequence_length + 1)
        if valid_samples == 0:
            return
            
        start_idx = len(self.global_entries)
        
        # Store episode data in memory (might be heavy if huge dataset, but fine for now)
        ep_data = {
            "path": ep_dir,
            "entries": entries,
            "images_main": ep_dir / "images_main",
            "images_wrist": ep_dir / "images_wrist"
        }
        self.episodes.append(ep_data)
        ep_idx = len(self.episodes) - 1
        
        # Map global indices
        for i in range(valid_samples):
            self.global_entries.append((ep_idx, i))

    def _load_image(self, path):
        if not path.exists():
            return np.zeros((224, 224, 3), dtype=np.uint8)
        img = cv2.imread(str(path))
        if img is None:
             return np.zeros((224, 224, 3), dtype=np.uint8)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = cv2.resize(img, (224, 224))
        return img

    def _get_qpos(self, entry):
        qpos_map = entry.get("qpos", {})
        return np.array([
            qpos_map.get('shoulder_pan', 0),
            qpos_map.get('shoulder_lift', 0),
            qpos_map.get('elbow_flex', 0),
            qpos_map.get('wrist_flex', 0),
            qpos_map.get('wrist_roll', 0),
            qpos_map.get('gripper', 0)
        ], dtype=np.float32)

    def __len__(self):
        return len(self.global_entries)

    def __getitem__(self, idx):
        ep_idx, local_idx = self.global_entries[idx]
        episode = self.episodes[ep_idx]
        entries = episode["entries"]
        
        # 1. Load History (Images & State)
        # Shape: [History, C, H, W] for images, [History, ActionDim] for state
        images_hist = []  # List of [2, C, H, W] (cameras) -> will act as channels
        state_hist = []
        
        for k in range(self.history_length):
            # history calculates backwards: current idx minus (history_len - 1 - k)
            # e.g. len=2. k=0 -> idx-1. k=1 -> idx.
            hist_idx = local_idx - (self.history_length - 1 - k)
            hist_idx = max(0, hist_idx) # Clamp to 0
            
            entry = entries[hist_idx]
            
            # Load Main Camera
            img_main_path = episode["images_main"] / entry.get("image_main", "")
            img_main = self._load_image(img_main_path)
            
            # Load Wrist Camera (Check if exists, else blank)
            img_wrist_path = episode["images_wrist"] / entry.get("image_wrist", "")
            img_wrist = self._load_image(img_wrist_path)
            
            # Normalize
            img_main_t = torch.from_numpy(img_main).permute(2, 0, 1).float() / 255.0
            img_wrist_t = torch.from_numpy(img_wrist).permute(2, 0, 1).float() / 255.0
            
            # Stack cameras channel-wise or list?
            # Model expects [NumCameras, History, C, H, W]
            images_hist.append(torch.stack([img_main_t, img_wrist_t]))
            
            # State
            qpos = self._get_qpos(entry)
            state_hist.append(torch.from_numpy(qpos))

        # Stack History: [History, NumCams, C, H, W] -> Permute to [NumCams, History, C, H, W]
        images_hist = torch.stack(images_hist).permute(1, 0, 2, 3, 4)
        state_hist = torch.stack(state_hist) # [History, ActionDim]
        
        # 2. Load Action Chunk (Future positions)
        actions = []
        for i in range(self.sequence_length):
            future_idx = local_idx + i
            if future_idx < len(entries):
                entry = entries[future_idx]
                actions.append(self._get_qpos(entry))
            else:
                # Pad with last action
                actions.append(actions[-1] if actions else np.zeros(6, dtype=np.float32))
                
        actions_t = torch.from_numpy(np.array(actions)) # [Horizon, ActionDim]
        
        return {
            "images": images_hist,
            "state": state_hist,
            "actions": actions_t
        }
